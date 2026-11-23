from agent_playground.evaluator import expected_demo_failure, security_checks_passed
from agent_playground.models import RunResult


def test_expected_demo_failure_requires_pytest_failure():
    assert expected_demo_failure(RunResult(("pytest",), 1, "1 failed", ""))


def test_expected_demo_failure_rejects_timeout():
    assert not expected_demo_failure(RunResult(("pytest",), 124, "1 failed", "", timed_out=True))


def test_security_evaluator_requires_every_check():
    output = "\n".join([
        "PASS: non_root",
        "PASS: root_filesystem_read_only",
        "PASS: workspace_writable",
        "PASS: network_disabled",
    ])
    assert security_checks_passed(RunResult(("python",), 0, output, ""))
    assert not security_checks_passed(
        RunResult(("python",), 0, output.replace("network_disabled", "missing"), "")
    )
