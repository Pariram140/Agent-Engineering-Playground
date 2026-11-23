import pytest

from agent_playground.contracts import ResourceLimits, TaskRequest


def test_task_request_round_trips_through_dict():
    request = TaskRequest(
        task_id="task-001",
        task_type="command",
        command=("python", "-m", "pytest", "-q"),
        input_files={"src/main.py": "print('hello')"},
        resource_limits=ResourceLimits(timeout_seconds=15, memory_mb=128),
    )
    assert TaskRequest.from_dict(request.to_dict()) == request


def test_rejects_path_traversal_and_windows_separators():
    for path in ("../secret.txt", "/etc/passwd", "folder\\\\secret.txt"):
        with pytest.raises(ValueError):
            TaskRequest("task-1", "command", ("python",), {path: "no"})


def test_rejects_unknown_fields_and_unbounded_limits():
    with pytest.raises(ValueError, match="unknown"):
        TaskRequest.from_dict({"task_id": "x", "task_type": "command", "command": ["python"], "admin": True})
    with pytest.raises(ValueError, match="timeout_seconds"):
        ResourceLimits(timeout_seconds=301)


def test_command_must_be_an_argument_array():
    with pytest.raises(ValueError, match="array"):
        TaskRequest.from_dict({"task_id": "task-1", "task_type": "command", "command": "python -c pass"})
