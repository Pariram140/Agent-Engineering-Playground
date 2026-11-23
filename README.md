# Agent Engineering Playground

A build-first learning project for understanding agent harness engineering, execution sandboxing, evaluation, observability, and security.

## Sandbox controls
- Non-root container user, network disabled, read-only container root filesystem
- Explicit writable /workspace, dropped Linux capabilities, and no-new-privileges
- Per-request CPU, memory, PID, and wall-clock timeout limits bounded by the contract
- Disposable named containers and temporary workspaces

## Setup
Windows 10/11 with PowerShell, Python 3.10+, and Docker Desktop using Linux containers:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest -q
```

Build and verify:
```powershell
python -m agent_playground build
python -m agent_playground security-check
python -m agent_playground demo
```

## Task request execution
Use TaskRequest (or its JSON-friendly dictionary form) with run_task. Commands are argument arrays passed directly to Docker without a shell. Input files are safely created inside a unique temporary workspace, which is removed after execution.

```python
from agent_playground.contracts import TaskRequest, ResourceLimits
from agent_playground.execution import run_task

request = TaskRequest(
    task_id="task-001",
    task_type="command",
    command=("python", "-c", "print(open('input.txt').read())"),
    input_files={"input.txt": "hello"},
    resource_limits=ResourceLimits(timeout_seconds=20, memory_mb=256, cpu_cores=0.5, pids=64),
)
result = run_task(request)
print(result.to_dict())
```

The result contains task_id, terminal status (succeeded, failed, timed_out, or cancelled), exit code when available, captured stdout/stderr, duration, and an error when applicable. Invalid contracts raise ValueError before Docker starts. Valid requests that fail to prepare or execute return a structured failed result.

Resource limits are bounded: timeout 1–300 seconds, memory 32–2048 MiB, CPU 0.1–4 cores, and PIDs 1–256. Every task retains the existing Docker isolation settings.

## Security scope
This is an educational local MVP, not hardened multi-tenant isolation. Docker shares the host kernel. Do not mount sensitive host paths, expose Docker credentials/socket, or pass secrets into untrusted tasks. Stronger isolation and adversarial escape testing remain future work.
