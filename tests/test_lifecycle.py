import pytest

from agent_playground.lifecycle import ExecutionLifecycle, ExecutionStatus, TaskResult


def test_happy_path_records_each_lifecycle_state():
    state = ExecutionLifecycle("task-1")
    state = state.transition(ExecutionStatus.VALIDATED)
    state = state.transition(ExecutionStatus.RUNNING)
    state = state.transition(ExecutionStatus.SUCCEEDED)
    assert state.history == (
        ExecutionStatus.CREATED,
        ExecutionStatus.VALIDATED,
        ExecutionStatus.RUNNING,
        ExecutionStatus.SUCCEEDED,
    )


def test_terminal_state_cannot_transition_again():
    state = ExecutionLifecycle("task-1").transition(ExecutionStatus.FAILED)
    with pytest.raises(ValueError, match="invalid execution transition"):
        state.transition(ExecutionStatus.RUNNING)


def test_result_requires_terminal_status_and_serializes_enum():
    with pytest.raises(ValueError, match="terminal"):
        TaskResult("task-1", ExecutionStatus.RUNNING)
    result = TaskResult("task-1", ExecutionStatus.TIMED_OUT, exit_code=124, duration_ms=30001)
    assert result.to_dict()["status"] == "timed_out"
