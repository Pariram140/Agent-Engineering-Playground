"""Validated, JSON-friendly contracts for deterministic task execution."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any

_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class ResourceLimits:
    """Resource ceilings requested for one task; values are intentionally bounded."""

    timeout_seconds: int = 20
    memory_mb: int = 256
    cpu_cores: float = 0.5
    pids: int = 64

    def __post_init__(self) -> None:
        if not isinstance(self.timeout_seconds, int) or isinstance(self.timeout_seconds, bool) or not 1 <= self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be an integer between 1 and 300")
        if not isinstance(self.memory_mb, int) or isinstance(self.memory_mb, bool) or not 32 <= self.memory_mb <= 2048:
            raise ValueError("memory_mb must be an integer between 32 and 2048")
        if not isinstance(self.cpu_cores, (int, float)) or isinstance(self.cpu_cores, bool) or not 0.1 <= self.cpu_cores <= 4.0:
            raise ValueError("cpu_cores must be between 0.1 and 4.0")
        if not isinstance(self.pids, int) or isinstance(self.pids, bool) or not 1 <= self.pids <= 256:
            raise ValueError("pids must be an integer between 1 and 256")


@dataclass(frozen=True)
class TaskRequest:
    """A task request. Commands are argument arrays, never shell command strings."""

    task_id: str
    task_type: str
    command: tuple[str, ...]
    input_files: dict[str, str] = field(default_factory=dict)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not _TASK_ID.fullmatch(self.task_id):
            raise ValueError("task_id must be 1-64 safe identifier characters")
        if self.task_type != "command":
            raise ValueError("task_type must be 'command' in this MVP")
        if not isinstance(self.command, tuple) or not self.command or any(
            not isinstance(part, str) or not part or "\x00" in part for part in self.command
        ):
            raise ValueError("command must be a non-empty tuple of non-empty strings")
        if not isinstance(self.input_files, dict):
            raise ValueError("input_files must be an object")
        for name, content in self.input_files.items():
            if not isinstance(name, str):
                raise ValueError("input file names must be strings")
            path = PurePosixPath(name)
            if (
                not name
                or "\\" in name
                or path.is_absolute()
                or any(part in ("", ".", "..") for part in path.parts)
            ):
                raise ValueError(f"input file path must be a safe relative POSIX path: {name!r}")
            if not isinstance(content, str):
                raise ValueError(f"input file content for {name!r} must be text")
        if not isinstance(self.resource_limits, ResourceLimits):
            raise ValueError("resource_limits must be a ResourceLimits instance")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this request."""
        data = asdict(self)
        data["command"] = list(self.command)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRequest":
        """Parse an untrusted mapping and validate every contract field."""
        if not isinstance(data, dict):
            raise ValueError("task request must be an object")
        expected = {"task_id", "task_type", "command", "input_files", "resource_limits"}
        unknown = set(data) - expected
        if unknown:
            raise ValueError(f"unknown task request fields: {', '.join(sorted(unknown))}")
        required = {"task_id", "task_type", "command"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"missing task request fields: {', '.join(sorted(missing))}")
        limits_data = data.get("resource_limits", {})
        if not isinstance(limits_data, dict):
            raise ValueError("resource_limits must be an object")
        try:
            limits = ResourceLimits(**limits_data)
            command = data["command"]
            if not isinstance(command, (list, tuple)):
                raise ValueError("command must be an array of arguments")
            input_files = data.get("input_files", {})
            if not isinstance(input_files, dict):
                raise ValueError("input_files must be an object")
            return cls(
                task_id=data["task_id"],
                task_type=data["task_type"],
                command=tuple(command),
                input_files=input_files,
                resource_limits=limits,
            )
        except TypeError as exc:
            raise ValueError(f"invalid task request structure: {exc}") from exc
