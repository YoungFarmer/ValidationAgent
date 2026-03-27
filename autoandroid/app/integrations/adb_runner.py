import subprocess


class AdbRunner:
    def run(self, args: list[str]) -> dict:
        command = ["adb", *args]
        completed = subprocess.run(command, capture_output=True, text=True)
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": command,
        }
