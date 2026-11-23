from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from agent_playground.models import RunResult

ROOT = Path(__file__).resolve().parents[2]
IMAGE_NAME = "agent-playground-sandbox:local"
RUNS_DIR = ROOT / ".playground" / "runs"


class HarnessError(RuntimeError):
    pass


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def ensure_image() -> None:
    if not _docker_available():
        raise HarnessError("Docker CLI was not found. Install/start Docker Desktop and reopen PowerShell.")

    inspect = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode == 0:
        return

    print(f"Building sandbox image: {IMAGE_NAME}")
    build = subprocess.run(
        ["docker", "build", "-f", "Dockerfile.sandbox", "-t", IMAGE_NAME, "."],
        cwd=ROOT,
        text=True,
        check=False,
    )
    if build.returncode != 0:
        raise HarnessError("Docker image build failed.")


def _run_container(workspace: Path, command: list[str], timeout_seconds: int = 20) -> RunResult:
    docker_command = [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--mount", f"type=bind,source={workspace.resolve()},target=/workspace",
        "--workdir", "/workspace",
        "--user", "10001:10001",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "64",
        "--memory", "256m",
        "--cpus", "0.50",
        IMAGE_NAME,
        *command,
    ]

    try:
        completed = subprocess.run(
            docker_command, cwd=ROOT, capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
        )
        return RunResult(tuple(command), completed.returncode, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return RunResult(tuple(command), 124, stdout, stderr, timed_out=True)


def run_demo() -> RunResult:
    ensure_image()
    demo_source = ROOT / "examples" / "demo"
    if not demo_source.is_dir():
        raise HarnessError(f"Demo task directory is missing: {demo_source}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="demo-", dir=RUNS_DIR) as temp_dir:
        workspace = Path(temp_dir)
        shutil.copytree(demo_source, workspace, dirs_exist_ok=True)
        return _run_container(workspace, ["python", "-m", "pytest", "-q"])


def run_security_probe() -> RunResult:
    ensure_image()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    probe = (
        "import os, socket\n"
        "checks = {}\n"
        "checks['non_root'] = (os.geteuid() != 0)\n"
        "checks['root_filesystem_read_only'] = bool(os.statvfs('/').f_flag & getattr(os, 'ST_RDONLY', 1))\n"
        "try:\n"
        "    with open('/workspace/probe.txt', 'w', encoding='utf-8') as f: f.write('ok')\n"
        "    checks['workspace_writable'] = True\n"
        "except OSError:\n"
        "    checks['workspace_writable'] = False\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 443), timeout=1)\n"
        "    checks['network_disabled'] = False\n"
        "except OSError:\n"
        "    checks['network_disabled'] = True\n"
        "for name, passed in checks.items(): print(('PASS' if passed else 'FAIL') + ': ' + name)\n"
        "raise SystemExit(0 if all(checks.values()) else 1)\n"
    )
    with tempfile.TemporaryDirectory(prefix="security-", dir=RUNS_DIR) as temp_dir:
        return _run_container(Path(temp_dir), ["python", "-c", probe], timeout_seconds=10)
