from agent_playground.contracts import ResourceLimits, TaskRequest
from agent_playground.execution import run_task
from agent_playground.lifecycle import ExecutionStatus


def test_task_runs_with_expected_docker_security_properties():
    probe = """import os, socket
assert os.geteuid() != 0
assert os.statvfs('/').f_flag & getattr(os, 'ST_RDONLY', 1)
assert open('input.txt', encoding='utf-8').read() == 'provided'
with open('output.txt', 'w', encoding='utf-8') as stream:
    stream.write('workspace is writable')
try:
    socket.create_connection(('1.1.1.1', 443), timeout=1)
except OSError:
    pass
else:
    raise AssertionError('network unexpectedly available')
print('sandbox-ok')
"""
    request = TaskRequest(
        task_id="docker-integration",
        task_type="command",
        command=("python", "-c", probe),
        input_files={"input.txt": "provided"},
        resource_limits=ResourceLimits(timeout_seconds=30, memory_mb=128, cpu_cores=0.5, pids=32),
    )

    result = run_task(request)

    assert result.status is ExecutionStatus.SUCCEEDED, result.to_dict()
    assert result.exit_code == 0
    assert "sandbox-ok" in result.stdout
    assert result.error is None
