import argparse
import json
import os
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
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="build the sandbox image")
    subparsers.add_parser("security-check", help="run the sandbox security probe")
    subparsers.add_parser("demo", help="run the intentionally failing demo")
    agent_parser = subparsers.add_parser("agent", help="plan one task with an OpenAI model and run it in Docker")
    agent_parser.add_argument("--prompt", required=True, help="task description for the agent")
    agent_parser.add_argument("--model", required=True, help="OpenAI API model identifier")
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

        if args.command == "demo":
            result = run_demo()
            _print_result(result)
            if expected_demo_failure(result):
                print("PASS: harness captured the expected failing test run.")
                return 0
            print("FAIL: demo did not produce the expected test-failure result.", file=sys.stderr)
            return 1

        if not os.environ.get("OPENAI_API_KEY"):
            print("ERROR: set OPENAI_API_KEY before using the agent command.", file=sys.stderr)
            return 2
        try:
            from openai import OpenAI
        except ImportError:
            print('ERROR: install the optional agent dependency with: python -m pip install -e ".[agent]"',
                  file=sys.stderr)
            return 2
        from agent_playground.agent import AgentError, run_agent

        result = run_agent(OpenAI(), args.prompt, args.model)
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.result.status.value == "succeeded" else 1

    except (HarnessError, AgentError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
