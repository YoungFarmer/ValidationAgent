import shlex
import subprocess


class GradleBuildAdapter:
    def __init__(self, command_runner=None):
        self._command_runner = command_runner or self._run_command

    def rebuild(self, request) -> dict:
        build_command = request.build.get("build_command", "./gradlew :app:assembleDebug")
        project_dir = request.build["project_dir"]
        command = shlex.split(build_command)
        result = self._command_runner(command, project_dir)
        return {
            "status": "rebuilt" if result["returncode"] == 0 else "failed",
            "artifact": request.build.get("ref", ""),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "command": result["command"],
        }

    def _run_command(self, command, cwd):
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": command,
        }
