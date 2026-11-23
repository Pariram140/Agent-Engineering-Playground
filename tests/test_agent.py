import json

import pytest

from agent_playground.agent import AgentError, plan_task, run_agent
from agent_playground.contracts import TaskRequest
from agent_playground.lifecycle import ExecutionStatus, TaskResult


class FakeResponses:
    def __init__(self, output):
        self.output = output
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return {"output": self.output}


class FakeClient:
    def __init__(self, output):
        self.responses = FakeResponses(output)


def function_call(arguments, name="run_sandbox_task"):
    return {"type": "function_call", "name": name, "arguments": json.dumps(arguments)}


def request_payload():
    return {
        "task_id": "agent-task-1",
        "task_type": "command",
        "command": ["python", "-c", "print('hello')"],
        "input_files": {},
        "resource_limits": {
            "timeout_seconds": 15, "memory_mb": 128, "cpu_cores": 0.5, "pids": 32
        },
    }


def test_plan_task_forces_one_function_and_validates_request():
    client = FakeClient([function_call(request_payload())])
    request = plan_task(client, "Print hello", "test-model")
    assert isinstance(request, TaskRequest)
    assert request.command == ("python", "-c", "print('hello')")
    assert client.responses.kwargs["tool_choice"] == {
        "type": "function", "name": "run_sandbox_task"
    }
    assert client.responses.kwargs["tools"][0]["strict"] is True


def test_agent_executes_only_the_validated_contract():
    client = FakeClient([function_call(request_payload())])
    seen = {}

    def execute(request):
        seen["request"] = request
        return TaskResult(request.task_id, ExecutionStatus.SUCCEEDED, 0, "hello\n")

    result = run_agent(client, "Print hello", "test-model", executor=execute)
    assert result.result.status is ExecutionStatus.SUCCEEDED
    assert seen["request"] == result.request
    assert result.to_dict()["request"]["task_id"] == "agent-task-1"


def test_invalid_model_request_never_reaches_executor():
    payload = request_payload()
    payload["input_files"] = {"../escape": "no"}
    client = FakeClient([function_call(payload)])
    with pytest.raises(AgentError, match="invalid task request"):
        run_agent(client, "do something", "test-model",
                  executor=lambda _: pytest.fail("executor must not run"))


@pytest.mark.parametrize("output", [[], [{"type": "message", "content": []}],
                                    [function_call(request_payload(), name="other")]])
def test_missing_or_wrong_function_call_fails_closed(output):
    with pytest.raises(AgentError, match="exactly one"):
        plan_task(FakeClient(output), "do something", "test-model")


@pytest.mark.parametrize("prompt,model", [("", "model"), ("prompt", ""), ("x" * 12001, "model")])
def test_prompt_and_model_are_bounded(prompt, model):
    client = FakeClient([])
    with pytest.raises(ValueError):
        plan_task(client, prompt, model)
