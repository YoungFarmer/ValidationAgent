import subprocess
from pathlib import Path


class CodexAdapter:
    def __init__(
        self,
        command_runner=None,
        workspace_root=".",
        output_last_message_path=None,
        timeout_seconds=120,
    ):
        self._command_runner = command_runner or self._run_command
        self._workspace_root = workspace_root
        self._output_last_message_path = Path(
            output_last_message_path or "autoandroid/runs/codex-last-message.txt"
        )
        self._timeout_seconds = timeout_seconds

    def send_repair_prompt(
        self,
        prompt: str,
        issues: list[dict],
        request_id: str,
        additional_writable_dirs: list[str] | None = None,
    ) -> dict:
        self._output_last_message_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--full-auto",
            "-C",
            self._workspace_root,
            "--output-last-message",
            str(self._output_last_message_path),
        ]
        for directory in additional_writable_dirs or []:
            if directory:
                command.extend(["--add-dir", directory])
        command.append(prompt)
        try:
            result = self._command_runner(command, prompt)
        except subprocess.TimeoutExpired as exc:
            result = {
                "returncode": 124,
                "stdout": self._decode_output(exc.output),
                "stderr": self._decode_output(exc.stderr),
                "command": exc.cmd,
                "timed_out": True,
                "timeout_seconds": exc.timeout,
            }
        last_message = ""
        if self._output_last_message_path.exists():
            last_message = self._output_last_message_path.read_text().strip()
        status = "submitted" if result["returncode"] == 0 else "failed"
        summary = {
            "status": status,
            "target": "codex",
            "request_id": request_id,
            "issue_count": len(issues),
            "prompt_preview": prompt.splitlines()[0] if prompt else "",
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "command": result["command"],
            "output_last_message_path": str(self._output_last_message_path),
            "last_message": last_message,
            "timed_out": result.get("timed_out", False),
            "timeout_seconds": result.get("timeout_seconds"),
        }
        return {
            "status": status,
            "target": "codex",
            "request_id": request_id,
            "issue_count": len(issues),
            "prompt_preview": prompt.splitlines()[0] if prompt else "",
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "command": result["command"],
            "output_last_message_path": str(self._output_last_message_path),
            "last_message": last_message,
            "timed_out": result.get("timed_out", False),
            "timeout_seconds": result.get("timeout_seconds"),
            "summary": summary,
        }

    def _run_command(self, command, prompt):
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=self._workspace_root,
            timeout=self._timeout_seconds,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": command,
        }

    def _decode_output(self, value):
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode(errors="replace")
        return value
