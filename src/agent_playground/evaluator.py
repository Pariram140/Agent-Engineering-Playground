from agent_playground.models import RunResult


def expected_demo_failure(result: RunResult) -> bool:
    """The demo is intentionally broken; pytest must report a test failure."""
    output = result.stdout + result.stderr
    return not result.timed_out and result.returncode == 1 and "failed" in output.lower()


def security_checks_passed(result: RunResult) -> bool:
    expected = {
        "PASS: non_root",
        "PASS: root_filesystem_read_only",
        "PASS: workspace_writable",
        "PASS: network_disabled",
    }
    output = result.stdout + result.stderr
    return result.succeeded and all(line in output for line in expected)
