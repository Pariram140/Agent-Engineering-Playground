# Agent Engineering Playground

A build-first learning project for understanding agent harness engineering, execution sandboxing, evaluation, observability, and security.

## Project approach

The first milestone uses a **deterministic Python harness without an LLM**. This isolates and validates execution controls before adding model-driven behavior.

- **Control plane (host):** creates a run workspace, starts the sandbox, applies limits, and collects results.
- **Execution plane (Docker):** runs task code in a disposable container as a non-root user.
- **Evaluator:** checks process results and expected security properties.
- **Human review:** inspects outputs before any future integration or deployment step.

## Initial sandbox controls

- Non-root container user
- Network disabled
- Read-only container root filesystem
- Explicit writable `/workspace`
- Linux capabilities dropped
- `no-new-privileges`
- CPU, memory, PID, and execution-time limits
- Disposable container lifecycle

## Prerequisites

- Windows 10/11 with PowerShell
- Python 3.10+
- Docker Desktop using Linux containers

## Local setup

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Run the host-side unit tests:

```powershell
python -m pytest -q
```

Build and verify the Docker sandbox:

```powershell
python -m agent_playground build
python -m agent_playground security-check
python -m agent_playground demo
```

Or run the full sequence with the PowerShell helper:

```powershell
.\verify-sandbox.ps1
```

The demo contains an intentionally defective discount function. The harness succeeds when it correctly captures the expected pytest failure; this demonstrates failure reporting, not a passing business-logic test.

If PowerShell blocks virtual-environment activation, use the appropriate execution-policy setting for your environment or invoke `.venv\Scripts\python.exe` directly.

## Learning roadmap

1. Validate deterministic sandbox execution and security checks.
2. Add structured task/result contracts and stronger evaluation.
3. Add an LLM agent that selects tools through the harness.
4. Add MCP integration, tracing, and an observability view.
5. Add adversarial tests and progressively stronger isolation.

## Security scope and limitations

This is an educational local MVP, **not** a hardened multi-tenant environment for running hostile code. Docker containers share the host kernel. Do not mount sensitive host paths, expose Docker credentials/socket, or pass secrets into untrusted tasks. Stronger isolation (for example, microVMs), hardened syscall policies, egress controls, image provenance, and adversarial escape testing are future work.

## Status

The deterministic harness and its security properties are the first milestone. LLM-driven autonomy comes later.
