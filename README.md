# Agent Engineering Playground

A build-first learning project for agent harness engineering, execution sandboxing, evaluation, and security.

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
python -m pip install -e ".[test,agent]"
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

## LLM agent
The optional agent asks an OpenAI model for one strict function call that produces a TaskRequest. The application validates that request with the same contract as direct callers, then sends it through run_task. The model cannot alter the Docker limits or isolation settings outside the bounded contract. No credentials are copied into the task container.

Set OPENAI_API_KEY in your environment and supply an API model identifier:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
agent-playground agent --model gpt-6.2-astra --prompt "Print hello from Python"
```

Model calls may incur API charges. Tests use a fake Responses API client and do not make network calls.

The result reports both the validated request and structured TaskResult. Invalid model output fails closed before Docker starts.

## Resource limits and security
Resource limits are bounded: timeout 1–300 seconds, memory 32–2048 MiB, CPU 0.1–4 cores, and PIDs 1–256. Every task retains the existing Docker isolation settings.

This is an educational local MVP, not hardened multi-tenant isolation. Docker shares the host kernel. Do not mount sensitive host paths, expose Docker credentials/socket, or pass secrets into untrusted tasks. Stronger isolation and adversarial escape testing remain future work.
