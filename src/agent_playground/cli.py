import argparse
import sys

from agent_playground.evaluator import expected_demo_failure, security_checks_passed
from agent_playground.harness import HarnessError, ensure_image, run_demo, run_security_probe


def _print_result(result) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="agent-playground",
        description="Build and verify a restricted Docker execution sandbox.",
    )
    parser.add_argument("command", choices=("build", "security-check", "demo"))
    args = parser.parse_args()

    try:
        if args.command == "build":
            ensure_image()
            print("Sandbox image is ready.")
            return 0

        if args.command == "security-check":
            result = run_security_probe()
            _print_result(result)
            if security_checks_passed(result):
                print("All sandbox security checks passed.")
                return 0
            print("One or more sandbox security checks failed.", file=sys.stderr)
            return 1

        result = run_demo()
        _print_result(result)
        if expected_demo_failure(result):
            print("PASS: harness captured the expected failing test run.")
            return 0
        print("FAIL: demo did not produce the expected test-failure result.", file=sys.stderr)
        return 1

    except HarnessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
