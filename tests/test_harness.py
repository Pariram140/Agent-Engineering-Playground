from agent_playground import harness


def test_docker_command_contains_expected_restrictions(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    result = harness._run_container(tmp_path, ["python", "--version"])
    command = captured["command"]

    assert "--network" in command and command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert "--cap-drop" in command and command[command.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in command and "no-new-privileges" in command
    assert result.succeeded
