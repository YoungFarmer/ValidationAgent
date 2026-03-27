from autoandroid.app.integrations.gradle_build_adapter import GradleBuildAdapter


class StubRunner:
    def __init__(self):
        self.calls = []

    def run(self, command, cwd):
        self.calls.append((command, cwd))
        return {"returncode": 0, "stdout": "BUILD SUCCESSFUL", "stderr": "", "command": command}


def test_gradle_build_adapter_runs_project_build_command():
    request = type(
        "Request",
        (),
        {
            "build": {
                "source_type": "gradle_project",
                "project_dir": "/Volumes/MySSD/sunflower",
                "build_command": "./gradlew :app:assembleDebug",
                "ref": "/Volumes/MySSD/sunflower/app/build/outputs/apk/debug/app-debug.apk",
            }
        },
    )()
    runner = StubRunner()
    adapter = GradleBuildAdapter(command_runner=runner.run)

    result = adapter.rebuild(request)

    assert runner.calls[0][0] == ["./gradlew", ":app:assembleDebug"]
    assert runner.calls[0][1] == "/Volumes/MySSD/sunflower"
    assert result["status"] == "rebuilt"
