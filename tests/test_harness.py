from __future__ import annotations

import subprocess

import pytest

from agent_playground import harness
from agent_playground.contracts import ResourceLimits


def test_docker_command_preserves_isolation_limits_and_argument_boundaries(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    limits = ResourceLimits(timeout_seconds=7, memory_mb=96, cpu_cores=0.25, pids=12)
    result = harness._run_container(
        tmp_path, ["python", "-c", "print('a b')"],
        resource_limits=limits, container_name="agent-task-test",
    )
    command = captured["command"]

    assert command[:5] == ["docker", "run", "--rm", "--name", "agent-task-test"]
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert command[command.index("--tmpfs") + 1].startswith("/tmp:")
    assert command[command.index("--user") + 1] == "10001:10001"
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert command[command.index("--security-opt") + 1] == "no-new-privileges"
    assert command[command.index("--pids-limit") + 1] == "12"
    assert command[command.index("--memory") + 1] == "96m"
    assert command[command.index("--cpus") + 1] == "0.25"
    assert command[-3:] == ["python", "-c", "print('a b')"]
    assert captured["kwargs"]["timeout"] == 7
    assert result.succeeded


def test_docker_workspace_mount_rejects_comma_paths(monkeypatch, tmp_path):
    workspace = tmp_path / "has,comma"
    workspace.mkdir()
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: pytest.fail("Docker must not run"))
    with pytest.raises(harness.HarnessError, match="comma"):
        harness._run_container(workspace, ["python", "--version"])


def test_timeout_force_removes_named_container(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["docker", "run", "--rm"]:
            raise subprocess.TimeoutExpired(command, timeout=1, output=b"partial", stderr=b"stuck")

        class Removed:
            returncode = 0
            stdout = ""
            stderr = ""

        return Removed()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    result = harness._run_container(
        tmp_path, ["python", "-c", "sleep"],
        resource_limits=ResourceLimits(timeout_seconds=1), container_name="agent-task-test",
    )
    assert result.timed_out and result.returncode == 124
    assert result.stdout == "partial" and result.stderr == "stuck"
    assert calls[1] == ["docker", "rm", "--force", "agent-task-test"]


def test_workspace_symlink_is_rejected(monkeypatch, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(harness.subprocess, "run", lambda *a, **k: pytest.fail("Docker must not run"))
    with pytest.raises(harness.HarnessError, match="real directory"):
        harness._run_container(link, ["python", "--version"])
