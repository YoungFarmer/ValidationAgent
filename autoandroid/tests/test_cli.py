import json

from autoandroid.app.cli import build_parser


def test_cli_parser_accepts_run_request_command():
    parser = build_parser()
    args = parser.parse_args(["run-request", "autoandroid/examples/requests/sunflower_launch_smoke.json"])

    assert args.command == "run-request"
    assert args.request_path.endswith("sunflower_launch_smoke.json")


def test_cli_parser_accepts_runs_root_override():
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-request",
            "autoandroid/examples/requests/sunflower_launch_smoke.json",
            "--runs-root",
            "/tmp/autoandroid-runs",
        ]
    )

    assert args.runs_root == "/tmp/autoandroid-runs"


def test_cli_parser_accepts_run_loop_command():
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-loop",
            "autoandroid/examples/requests/sunflower_launch_smoke.json",
            "--runs-root",
            "/tmp/autoandroid-runs",
        ]
    )

    assert args.command == "run-loop"
    assert args.runs_root == "/tmp/autoandroid-runs"


def test_cli_run_request_invokes_orchestrator(monkeypatch, capsys):
    called = {}

    class StubOrchestrator:
        def run_once(self, request):
            called["request_id"] = request.request_id
            return {"judgement": type("J", (), {"summary": {"final_status": "passed"}})()}

    class StubIntakeService:
        def load_request(self, path: str):
            called["path"] = path
            return type("R", (), {"request_id": "req_cli"})()

    def create_stub_orchestrator(runs_root=None):
        called["runs_root"] = runs_root
        return StubOrchestrator()

    monkeypatch.setattr("autoandroid.app.cli.create_default_orchestrator", create_stub_orchestrator)
    monkeypatch.setattr("autoandroid.app.cli.IntakeService", StubIntakeService)

    from autoandroid.app.cli import main

    exit_code = main(["run-request", "demo.json"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert called["path"] == "demo.json"
    assert called["request_id"] == "req_cli"
    assert called["runs_root"] is None
    assert "passed" in stdout


def test_cli_run_request_passes_runs_root_override(monkeypatch, capsys):
    called = {}

    class StubOrchestrator:
        def run_once(self, request):
            called["request_id"] = request.request_id
            return {"judgement": type("J", (), {"summary": {"final_status": "passed"}})()}

    class StubIntakeService:
        def load_request(self, path: str):
            called["path"] = path
            return type("R", (), {"request_id": "req_cli"})()

    monkeypatch.setattr(
        "autoandroid.app.cli.create_default_orchestrator",
        lambda runs_root=None: _record_runs_root(called, runs_root, StubOrchestrator()),
    )
    monkeypatch.setattr("autoandroid.app.cli.IntakeService", StubIntakeService)

    from autoandroid.app.cli import main

    exit_code = main(["run-request", "demo.json", "--runs-root", "/tmp/custom-runs"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert called["runs_root"] == "/tmp/custom-runs"
    assert "passed" in stdout


def test_create_default_orchestrator_uses_codex_adapter_by_default():
    from autoandroid.app.cli import create_default_orchestrator

    orchestrator = create_default_orchestrator()

    assert orchestrator._repair_adapter is not None
    assert orchestrator._repair_adapter.__class__.__name__ == "CodexAdapter"


def test_run_loop_persists_loop_trace_with_handoff_summary(monkeypatch, tmp_path):
    called = {}

    class StubRepairAdapter:
        def __init__(self):
            self.calls = []

        def send_repair_prompt(
            self,
            prompt,
            issues,
            request_id,
            additional_writable_dirs=None,
        ):
            self.calls.append((prompt, issues, request_id, additional_writable_dirs))
            return {
                "status": "submitted",
                "target": "codex",
                "request_id": request_id,
                "issue_count": len(issues),
                "prompt_preview": prompt.splitlines()[0],
                "summary": {
                    "status": "submitted",
                    "request_id": request_id,
                    "issue_count": len(issues),
                    "prompt_preview": prompt.splitlines()[0],
                },
            }

    class StubOrchestrator:
        def __init__(self):
            self._runs_root = tmp_path
            self._repair_adapter = StubRepairAdapter()

        def run_once(self, request, loop_index=1):
            loop_dir = self._runs_root / request.request_id / f"loop_{loop_index:02d}"
            loop_dir.mkdir(parents=True, exist_ok=True)
            (loop_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "request_id": request.request_id,
                        "loop_index": loop_index,
                        "final_status": "failed",
                        "run_id": f"run_{loop_index:03d}",
                        "plan_id": f"plan_{loop_index:03d}",
                    }
                )
            )
            if loop_index == 1:
                (loop_dir / "issues.json").write_text(
                    json.dumps(
                        [
                            {
                                "acceptance_item_id": "AC-001",
                                "title": "Launch app failed",
                                "failure_type": "product_bug",
                            }
                        ]
                    )
                )
                (loop_dir / "repair_prompt.md").write_text("Fix AC-001: launch app failed\n")
            return {"judgement": type("J", (), {"summary": {"final_status": "failed"}})()}

    class StubIntakeService:
        def load_request(self, path: str):
            called["path"] = path
            return type(
                "R",
                (),
                {
                    "request_id": "req_loop_trace",
                    "constraints": {"max_loops": 2},
                    "build": {
                        "source_type": "gradle_project",
                        "project_dir": "/tmp/project",
                        "ref": "/tmp/app-debug.apk",
                    },
                },
            )()

    class StubBuildAdapter:
        def rebuild(self, request):
            return {
                "status": "rebuilt",
                "artifact": request.build["ref"],
                "stdout": "BUILD SUCCESSFUL",
                "stderr": "",
                "command": ["./gradlew", ":app:assembleDebug"],
            }

    class StubLoopManager:
        def __init__(self, stop_conditions=None):
            called["stop_conditions"] = stop_conditions

        def run_loop(self, request, run_validation, repair_adapter, build_adapter):
            called["request_id"] = request.request_id
            called["repair_adapter"] = repair_adapter
            called["build_adapter"] = build_adapter
            trace = run_validation(1)
            called["trace"] = trace
            repair_adapter.send_repair_prompt(trace["repair_prompt"], trace["issues"], request.request_id)
            build_adapter.rebuild(request)
            return {"final_status": "blocked", "completed_loops": 1, "reason": "repair_handoff_failed"}

    monkeypatch.setattr("autoandroid.app.cli.create_default_orchestrator", lambda runs_root=None: StubOrchestrator())
    monkeypatch.setattr("autoandroid.app.cli.IntakeService", StubIntakeService)
    monkeypatch.setattr("autoandroid.app.cli.RepairLoopManager", StubLoopManager)
    monkeypatch.setattr("autoandroid.app.cli.GradleBuildAdapter", lambda: StubBuildAdapter())

    from autoandroid.app.cli import main

    exit_code = main(["run-loop", "demo.json", "--runs-root", str(tmp_path)])
    loop_trace_path = tmp_path / "req_loop_trace" / "loop_trace.json"
    trace_payload = json.loads(loop_trace_path.read_text())

    assert exit_code == 0
    assert called["path"] == "demo.json"
    assert trace_payload["final_status"] == "blocked"
    assert "/tmp/project" in called["trace"]["repair_prompt"]
    assert "/tmp/app-debug.apk" in called["trace"]["repair_prompt"]
    assert trace_payload["loops"][0]["repair_handoff"]["summary"]["issue_count"] == 1
    assert trace_payload["loops"][0]["repair_handoff"]["summary"]["status"] == "submitted"
    assert trace_payload["loops"][0]["rebuild"]["status"] == "rebuilt"


def _record_runs_root(called: dict, runs_root, orchestrator):
    called["runs_root"] = runs_root
    return orchestrator
