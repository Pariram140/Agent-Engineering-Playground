"""Explicit execution lifecycle and structured task results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


_TERMINAL = {
    ExecutionStatus.SUCCEEDED,
    ExecutionStatus.FAILED,
    ExecutionStatus.TIMED_OUT,
    ExecutionStatus.CANCELLED,
}
_ALLOWED = {
    ExecutionStatus.CREATED: {ExecutionStatus.VALIDATED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED},
    ExecutionStatus.VALIDATED: {ExecutionStatus.RUNNING, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED},
    ExecutionStatus.RUNNING: _TERMINAL,
}


@dataclass(frozen=True)
class ExecutionLifecycle:
    task_id: str
    status: ExecutionStatus = ExecutionStatus.CREATED
    history: tuple[ExecutionStatus, ...] = (ExecutionStatus.CREATED,)

    def transition(self, next_status: ExecutionStatus) -> "ExecutionLifecycle":
        """Return a new lifecycle snapshot, rejecting illegal state transitions."""
        if not isinstance(next_status, ExecutionStatus):
            raise ValueError("next_status must be an ExecutionStatus")
        if next_status not in _ALLOWED.get(self.status, set()):
            raise ValueError(f"invalid execution transition: {self.status.value} -> {next_status.value}")
        return ExecutionLifecycle(self.task_id, next_status, self.history + (next_status,))


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: ExecutionStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _TERMINAL:
            raise ValueError("TaskResult status must be terminal")
        if self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data
