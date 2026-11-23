"""Contract-driven Docker task execution."""
from __future__ import annotations

import os
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from agent_playground import harness
from agent_playground.contracts import TaskRequest
from agent_playground.lifecycle import ExecutionLifecycle, ExecutionStatus, TaskResult


def _safe_runs_dir() -> Path:
    """Create a private host parent for temporary task workspaces."""
    root = harness.ROOT.resolve()
    playground, runs = root / ".playground", root / ".playground" / "runs"
    for directory in (playground, runs):
        if directory.exists() and directory.is_symlink():
            raise OSError(f"workspace parent must not be a symlink: {directory}")
        directory.mkdir(mode=0o700, exist_ok=True)
        if not directory.resolve(strict=True).is_relative_to(root):
            raise OSError("workspace parent resolves outside the repository")
        # Keep host-side workspace names and contents private. Docker only sees
        # the individual workspace bind mount, whose permissions are adjusted
        # separately for the sandbox's fixed non-root UID.
        try:
            directory.chmod(0o700)
        except OSError:
            pass
    return runs


def _write_inputs(workspace: Path, files: dict[str, str]) -> None:
    """Write validated relative files with permissions usable by UID 10001."""
    root = workspace.resolve(strict=True)
    # TemporaryDirectory is normally 0700 for the host owner. The sandbox runs
    # as UID 10001, so make this isolated bind-mounted directory traversable and
    # writable; its parent remains private to the host user.
    root.chmod(0o777)
    for name, content in files.items():
        if not isinstance(name, str) or "\\" in name or ":" in name:
            raise ValueError(f"unsafe input file path: {name!r}")
        relative = PurePosixPath(name)
        if relative.is_absolute() or not relative.parts or any(
            part in ("", ".", "..") or part.endswith((".", " ")) for part in relative.parts
        ):
            raise ValueError(f"unsafe input file path: {name!r}")
        target = root.joinpath(*relative.parts)
        target.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
        if not target.parent.resolve(strict=True).is_relative_to(root) or target.is_symlink():
            raise ValueError(f"input file path escapes workspace: {name!r}")
        target.parent.chmod(0o777)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(target, flags, 0o666)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        target.chmod(0o666)


def run_task(request: TaskRequest | dict[str, Any]) -> TaskResult:
    """Validate, execute, and return a terminal structured result."""
    if isinstance(request, dict):
        request = TaskRequest.from_dict(request)
    elif isinstance(request, TaskRequest):
        request = TaskRequest.from_dict(request.to_dict())
    else:
        raise ValueError("request must be a TaskRequest or task request object")

    lifecycle = ExecutionLifecycle(request.task_id).transition(ExecutionStatus.VALIDATED)
    started = time.monotonic()
    name = f"agent-task-{uuid.uuid4().hex[:20]}"
    try:
        harness.ensure_image()
        with tempfile.TemporaryDirectory(prefix="task-", dir=_safe_runs_dir()) as temp_dir:
            workspace = Path(temp_dir)
            _write_inputs(workspace, request.input_files)
            lifecycle = lifecycle.transition(ExecutionStatus.RUNNING)
            run = harness._run_container(
                workspace, list(request.command),
                timeout_seconds=request.resource_limits.timeout_seconds,
                resource_limits=request.resource_limits, container_name=name,
            )
        status = (ExecutionStatus.TIMED_OUT if run.timed_out else
                  ExecutionStatus.SUCCEEDED if run.succeeded else ExecutionStatus.FAILED)
        lifecycle = lifecycle.transition(status)
        return TaskResult(request.task_id, lifecycle.status, run.returncode, run.stdout, run.stderr,
                          max(0, int((time.monotonic() - started) * 1000)),
                          "execution timed out" if run.timed_out else None)
    except KeyboardInterrupt:
        harness._stop_container(name)
        lifecycle = lifecycle.transition(ExecutionStatus.CANCELLED)
        return TaskResult(request.task_id, lifecycle.status,
                          duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                          error="execution cancelled")
    except Exception as exc:
        lifecycle = lifecycle.transition(ExecutionStatus.FAILED)
        return TaskResult(request.task_id, lifecycle.status,
                          duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                          error=f"{type(exc).__name__}: {exc}")
