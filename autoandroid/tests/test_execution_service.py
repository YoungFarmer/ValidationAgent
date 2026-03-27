from pathlib import Path

from autoandroid.app.models.plan import TestCase, TestPlan
from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.services.execution_service import ExecutionService


class StubMaestroRunner:
    def __init__(self):
        self.calls = []

    def run(self, flow_path: str, output_dir: str) -> dict:
        self.calls.append((flow_path, output_dir))
        return {"returncode": 0, "stdout": "ok", "stderr": "", "command": ["maestro", "test", flow_path]}


class StubAdbRunner:
    def __init__(self):
        self.calls = []

    def run(self, args: list[str]) -> dict:
        self.calls.append(args)
        return {"returncode": 0, "stdout": "ok", "stderr": "", "command": ["adb", *args]}


def test_execution_service_writes_maestro_flow_and_runs_commands(tmp_path):
    request = ValidationRequest(
        request_id="req_001",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "Launch app and show My garden"}],
        build={
            "source_type": "apk",
            "ref": "/Volumes/MySSD/sunflower/app/build/outputs/apk/debug/app-debug.apk",
            "app_id": "com.google.samples.apps.sunflower",
            "launch_activity": ".GardenActivity",
        },
        environment={"platform": "android", "mode": "connected_device"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )
    plan = TestPlan(
        plan_id="plan_001",
        spec_id="spec_001",
        cases=[
            TestCase(
                case_id="CASE-001",
                acceptance_item_id="AC-001",
                tooling={
                    "maestro_flow": str(tmp_path / "flows" / "ac-001.yaml"),
                    "adb_commands": [["shell", "am", "force-stop", "com.google.samples.apps.sunflower"]],
                },
                environment={"device_type": "connected_device"},
                assertions=["My garden", "Add plant"],
                artifacts=["screenshot"],
            )
        ],
    )
    maestro_runner = StubMaestroRunner()
    adb_runner = StubAdbRunner()

    run = ExecutionService(maestro_runner=maestro_runner, adb_runner=adb_runner).execute(request, plan)

    flow_path = Path(plan.cases[0].tooling["maestro_flow"])

    assert run.status == "finished"
    assert flow_path.exists()
    assert "assertVisible: \"My garden\"" in flow_path.read_text()
    assert adb_runner.calls[0] == ["install", "-r", "/Volumes/MySSD/sunflower/app/build/outputs/apk/debug/app-debug.apk"]
    assert maestro_runner.calls[0][0] == str(flow_path)
