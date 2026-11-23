from agent_playground import execution, harness
from agent_playground.contracts import ResourceLimits, TaskRequest
from agent_playground.lifecycle import ExecutionStatus
from agent_playground.models import RunResult
import pytest

def make_request(files=None):
    return TaskRequest("task-1", "command", ("python", "-c", "print('ok')"),
                       files or {"nested/input.txt": "payload"},
                       ResourceLimits(timeout_seconds=7, memory_mb=96, cpu_cores=.25, pids=12))

def test_success_writes_inputs_and_passes_limits(monkeypatch, tmp_path):
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "ensure_image", lambda: None)
    seen = {}
    def run(workspace, command, **kwargs):
        seen.update(command=command, kwargs=kwargs, input=(workspace / "nested/input.txt").read_text(),
                    workspace=workspace)
        return RunResult(tuple(command), 0, "ok\n", "")
    monkeypatch.setattr(harness, "_run_container", run)
    result = execution.run_task(make_request())
    assert result.status is ExecutionStatus.SUCCEEDED and result.exit_code == 0
    assert seen["input"] == "payload" and seen["command"][0] == "python"
    assert seen["kwargs"]["resource_limits"].memory_mb == 96
    assert seen["kwargs"]["timeout_seconds"] == 7
    assert not seen["workspace"].exists()

@pytest.mark.parametrize("run_result,status", [
    (RunResult(("x",), 2, "", "bad"), ExecutionStatus.FAILED),
    (RunResult(("x",), 124, "partial", "", True), ExecutionStatus.TIMED_OUT),
])
def test_failure_and_timeout_mapping(monkeypatch, tmp_path, run_result, status):
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "ensure_image", lambda: None)
    monkeypatch.setattr(harness, "_run_container", lambda *a, **k: run_result)
    result = execution.run_task(make_request({}))
    assert result.status is status
    assert result.exit_code == run_result.returncode
    assert (result.error is not None) == run_result.timed_out

def test_invalid_request_rejected_before_docker(monkeypatch):
    monkeypatch.setattr(harness, "ensure_image", lambda: pytest.fail("must not run"))
    with pytest.raises(ValueError):
        execution.run_task({"task_id":"task-1","task_type":"command","command":["python"],
                            "input_files":{"../escape":"x"}})

def test_symlink_parent_and_file_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        execution._write_inputs(ws, {"link/payload.txt":"x"})
    target = tmp_path / "target"
    target.write_text("safe")
    (ws / "file").symlink_to(target)
    with pytest.raises((ValueError, OSError)):
        execution._write_inputs(ws, {"file":"overwrite"})
    assert target.read_text() == "safe"

def test_rejects_windows_alternate_stream(tmp_path):
    with pytest.raises(ValueError):
        execution._write_inputs(tmp_path, {"file.txt:stream":"x"})
