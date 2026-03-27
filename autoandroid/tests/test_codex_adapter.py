import subprocess
from pathlib import Path

from autoandroid.app.integrations.codex_adapter import CodexAdapter


class StubRunner:
    def __init__(self):
        self.calls = []

    def run(self, command, prompt):
        self.calls.append((command, prompt))
        return {
            "returncode": 0,
            "stdout": '{"status":"submitted"}',
            "stderr": "",
            "command": command,
        }


def test_codex_adapter_invokes_codex_exec_with_prompt_and_output_file(tmp_path):
    output_file = tmp_path / "codex-last-message.txt"
    runner = StubRunner()
    adapter = CodexAdapter(
        command_runner=runner.run,
        workspace_root="/Volumes/MySSD/project/AutoAndroid/.worktrees/android-validation-agent-mvp",
        output_last_message_path=output_file,
    )

    result = adapter.send_repair_prompt(
        prompt="Fix AC-001: launch flow failed",
        issues=[{"acceptance_item_id": "AC-001"}],
        request_id="req_001",
    )

    command, prompt = runner.calls[0]

    assert command[:2] == ["codex", "exec"]
    assert "--full-auto" in command
    assert "--output-last-message" in command
    assert str(output_file) in command
    assert prompt == "Fix AC-001: launch flow failed"
    assert result["status"] == "submitted"


def test_codex_adapter_marks_failed_when_cli_returns_nonzero(tmp_path):
    output_file = tmp_path / "codex-last-message.txt"

    def failing_runner(command, prompt):
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": "authentication error",
            "command": command,
        }

    adapter = CodexAdapter(
        command_runner=failing_runner,
        workspace_root="/Volumes/MySSD/project/AutoAndroid/.worktrees/android-validation-agent-mvp",
        output_last_message_path=output_file,
    )

    result = adapter.send_repair_prompt(
        prompt="Fix AC-001: launch flow failed",
        issues=[{"acceptance_item_id": "AC-001"}],
        request_id="req_002",
    )

    assert result["status"] == "failed"
    assert "authentication error" in result["stderr"]


def test_codex_adapter_reads_output_last_message_when_present(tmp_path):
    output_file = tmp_path / "codex-last-message.txt"

    def runner(command, prompt):
        output_file.write_text("Applied a fix to the validation target.")
        return {
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "command": command,
        }

    adapter = CodexAdapter(
        command_runner=runner,
        workspace_root="/Volumes/MySSD/project/AutoAndroid/.worktrees/android-validation-agent-mvp",
        output_last_message_path=output_file,
    )

    result = adapter.send_repair_prompt(
        prompt="Fix AC-001: launch flow failed",
        issues=[{"acceptance_item_id": "AC-001"}],
        request_id="req_003",
    )

    assert result["last_message"] == "Applied a fix to the validation target."


def test_codex_adapter_exposes_audit_summary(tmp_path):
    output_file = tmp_path / "codex-last-message.txt"
    commands = []

    def runner(command, prompt):
        commands.append((command, prompt))
        output_file.write_text("Applied a fix to the validation target.")
        return {
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "command": command,
        }

    adapter = CodexAdapter(
        command_runner=runner,
        workspace_root="/Volumes/MySSD/project/AutoAndroid/.worktrees/android-validation-agent-mvp",
        output_last_message_path=output_file,
    )

    result = adapter.send_repair_prompt(
        prompt="Fix AC-001: launch flow failed",
        issues=[{"acceptance_item_id": "AC-001"}],
        request_id="req_004",
        additional_writable_dirs=["/Volumes/MySSD/sunflower"],
    )

    assert result["summary"]["status"] == "submitted"
    assert result["summary"]["issue_count"] == 1
    assert result["summary"]["prompt_preview"] == "Fix AC-001: launch flow failed"
    assert result["summary"]["last_message"] == "Applied a fix to the validation target."

    command, _ = commands[0]
    assert "--add-dir" in command
    assert "/Volumes/MySSD/sunflower" in command


def test_codex_adapter_marks_timeout_as_failed(tmp_path):
    output_file = tmp_path / "codex-last-message.txt"

    def timeout_runner(command, prompt):
        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=7,
            output="partial stdout",
            stderr="partial stderr",
        )

    adapter = CodexAdapter(
        command_runner=timeout_runner,
        workspace_root="/Volumes/MySSD/project/AutoAndroid/.worktrees/android-validation-agent-mvp",
        output_last_message_path=output_file,
    )

    result = adapter.send_repair_prompt(
        prompt="Fix AC-001: launch flow failed",
        issues=[{"acceptance_item_id": "AC-001"}],
        request_id="req_005",
    )

    assert result["status"] == "failed"
    assert result["timed_out"] is True
    assert result["timeout_seconds"] == 7
    assert result["stdout"] == "partial stdout"
    assert result["stderr"] == "partial stderr"
