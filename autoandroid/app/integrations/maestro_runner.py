import subprocess


class MaestroRunner:
    def run(self, flow_path: str, output_dir: str) -> dict:
        command = ["maestro", "test", flow_path, f"--test-output-dir={output_dir}"]
        completed = subprocess.run(command, capture_output=True, text=True)
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": command,
        }
