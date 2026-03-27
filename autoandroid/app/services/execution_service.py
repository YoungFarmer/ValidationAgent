from datetime import datetime
from pathlib import Path

from autoandroid.app.models.run import CaseResult, ExecutionRun


class ExecutionService:
    def __init__(self, maestro_runner, adb_runner):
        self._maestro_runner = maestro_runner
        self._adb_runner = adb_runner

    def execute(self, request, plan) -> ExecutionRun:
        build_ref = request.build.get("ref", "")
        if build_ref:
            self._adb_runner.run(["install", "-r", build_ref])

        case_results = []
        started_at = datetime.now().astimezone().isoformat()

        for case in plan.cases:
            flow_path = Path(case.tooling["maestro_flow"])
            output_dir = flow_path.parent.parent / "artifacts" / case.case_id.lower()
            self._write_flow_file(flow_path, request.build.get("app_id", ""), case.assertions)

            for command in case.tooling.get("adb_commands", []):
                self._adb_runner.run(command)

            maestro_result = self._maestro_runner.run(str(flow_path), str(output_dir))
            case_status = "passed" if maestro_result["returncode"] == 0 else "failed"
            case_results.append(
                CaseResult(
                    case_id=case.case_id,
                    status=case_status,
                    steps=[
                        {
                            "name": "run maestro flow",
                            "status": case_status,
                        }
                    ],
                    artifacts={
                        "flow_path": str(flow_path),
                        "output_dir": str(output_dir),
                        "stdout": maestro_result["stdout"],
                        "stderr": maestro_result["stderr"],
                    },
                )
            )

        finished_at = datetime.now().astimezone().isoformat()
        return ExecutionRun(
            run_id="run_001",
            request_id=request.request_id,
            plan_id=plan.plan_id,
            status="finished",
            device={"kind": request.environment.get("mode", "unknown"), "serial": "active-device"},
            started_at=started_at,
            finished_at=finished_at,
            case_results=case_results,
        )

    def _write_flow_file(self, flow_path: Path, app_id: str, assertions: list[str]) -> None:
        flow_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"appId: {app_id}", "---", "- launchApp"]
        for assertion in assertions:
            lines.append(f'- assertVisible: "{assertion}"')
        flow_path.write_text("\n".join(lines) + "\n")
