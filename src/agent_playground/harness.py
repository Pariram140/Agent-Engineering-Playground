from __future__ import annotations
import shutil, subprocess, tempfile
from pathlib import Path
from agent_playground.contracts import ResourceLimits
from agent_playground.models import RunResult
ROOT = Path(__file__).resolve().parents[2]
IMAGE_NAME = "agent-playground-sandbox:local"
RUNS_DIR = ROOT / ".playground" / "runs"
class HarnessError(RuntimeError): pass
def _docker_available() -> bool:
    return shutil.which("docker") is not None
def ensure_image() -> None:
    if not _docker_available():
        raise HarnessError("Docker CLI was not found. Install/start Docker Desktop and reopen PowerShell.")
    inspect = subprocess.run(["docker","image","inspect",IMAGE_NAME],capture_output=True,text=True,check=False)
    if inspect.returncode == 0: return
    print(f"Building sandbox image: {IMAGE_NAME}")
    build = subprocess.run(["docker","build","-f","Dockerfile.sandbox","-t",IMAGE_NAME,"."],cwd=ROOT,text=True,check=False)
    if build.returncode != 0: raise HarnessError("Docker image build failed.")
def _stop_container(name: str) -> None:
    try:
        subprocess.run(["docker","rm","--force",name],cwd=ROOT,capture_output=True,text=True,timeout=10,check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass
def _run_container(workspace: Path, command: list[str], timeout_seconds: int = 20,
                   resource_limits: ResourceLimits | None = None, container_name: str | None = None) -> RunResult:
    limits = resource_limits or ResourceLimits(timeout_seconds=timeout_seconds)
    resolved = workspace.resolve(strict=True)
    if not resolved.is_dir() or workspace.is_symlink():
        raise HarnessError("Task workspace must be an existing real directory.")
    if "," in str(resolved):
        raise HarnessError("Task workspace path contains an unsupported comma.")
    docker_command = ["docker","run","--rm"]
    if container_name: docker_command.extend(["--name",container_name])
    docker_command.extend([
        "--network","none","--read-only","--tmpfs","/tmp:rw,noexec,nosuid,size=16m",
        "--mount",f"type=bind,source={resolved},target=/workspace","--workdir","/workspace",
        "--user","10001:10001","--cap-drop","ALL","--security-opt","no-new-privileges",
        "--pids-limit",str(limits.pids),"--memory",f"{limits.memory_mb}m",
        "--cpus",f"{limits.cpu_cores:.2f}",IMAGE_NAME,*command])
    try:
        completed = subprocess.run(docker_command,cwd=ROOT,capture_output=True,text=True,
                                   timeout=limits.timeout_seconds,check=False)
        return RunResult(tuple(command),completed.returncode,completed.stdout,completed.stderr)
    except subprocess.TimeoutExpired as exc:
        if container_name: _stop_container(container_name)
        stdout, stderr = exc.stdout or "", exc.stderr or ""
        if isinstance(stdout,bytes): stdout = stdout.decode(errors="replace")
        if isinstance(stderr,bytes): stderr = stderr.decode(errors="replace")
        return RunResult(tuple(command),124,stdout,stderr,timed_out=True)
def run_demo() -> RunResult:
    ensure_image()
    source = ROOT / "examples" / "demo"
    if not source.is_dir(): raise HarnessError(f"Demo task directory is missing: {source}")
    RUNS_DIR.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="demo-",dir=RUNS_DIR) as temp_dir:
        workspace=Path(temp_dir); shutil.copytree(source,workspace,dirs_exist_ok=True)
        return _run_container(workspace,["python","-m","pytest","-q"])
def run_security_probe() -> RunResult:
    ensure_image(); RUNS_DIR.mkdir(parents=True,exist_ok=True)
    probe=("import os, socket\nchecks = {}\nchecks['non_root'] = (os.geteuid() != 0)\n"
      "checks['root_filesystem_read_only'] = bool(os.statvfs('/').f_flag & getattr(os, 'ST_RDONLY', 1))\n"
      "try:\n    with open('/workspace/probe.txt', 'w', encoding='utf-8') as f: f.write('ok')\n    checks['workspace_writable'] = True\n"
      "except OSError:\n    checks['workspace_writable'] = False\ntry:\n    socket.create_connection(('1.1.1.1', 443), timeout=1)\n    checks['network_disabled'] = False\n"
      "except OSError:\n    checks['network_disabled'] = True\nfor name, passed in checks.items(): print(('PASS' if passed else 'FAIL') + ': ' + name)\n"
      "raise SystemExit(0 if all(checks.values()) else 1)\n")
    with tempfile.TemporaryDirectory(prefix="security-",dir=RUNS_DIR) as temp_dir:
        return _run_container(Path(temp_dir),["python","-c",probe],timeout_seconds=10)
