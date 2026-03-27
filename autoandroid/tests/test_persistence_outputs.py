import json

from autoandroid.app.models.issue import IssueReport
from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.models.run import CaseResult, ExecutionRun, JudgementResult
from autoandroid.app.models.spec import AcceptanceItem, AcceptanceSpec
from autoandroid.app.models.plan import TestCase, TestPlan
from autoandroid.app.orchestrator import Orchestrator


class StubSpecBuilder:
    def build(self, request):
        return AcceptanceSpec(
            spec_id="spec_001",
            feature_name=request.feature_name,
            in_scope=["launch app"],
            out_of_scope=[],
            acceptance_items=[
                AcceptanceItem(
                    id="AC-001",
                    title="Launch app",
                    type="ui",
                    priority="high",
                    preconditions=[],
                    steps=["launch app"],
                    expected=["Sunflower visible"],
                    evidence=["screenshot"],
                )
            ],
        )


class StubTestPlanner:
    def build(self, spec):
        return TestPlan(
            plan_id="plan_001",
            spec_id=spec.spec_id,
            cases=[
                TestCase(
                    case_id="CASE-001",
                    acceptance_item_id="AC-001",
                    tooling={"maestro_flow": "autoandroid/flows/generated/ac-001.yaml", "adb_commands": []},
                    environment={"device_type": "emulator"},
                    assertions=["Sunflower visible"],
                    artifacts=["screenshot"],
                )
            ],
        )


class StubExecutionService:
    def execute(self, request, plan):
        return ExecutionRun(
            run_id="run_001",
            request_id=request.request_id,
            plan_id=plan.plan_id,
            status="finished",
            device={"kind": "emulator", "serial": "stub-emulator"},
            started_at="2026-03-26T10:00:00+08:00",
            finished_at="2026-03-26T10:01:00+08:00",
            case_results=[
                CaseResult(
                    case_id="CASE-001",
                    status="passed",
                    steps=[],
                    artifacts={"stderr": ""},
                )
            ],
        )


class StubJudgementService:
    def judge(self, spec, run):
        return JudgementResult(
            judgement_id="judge_001",
            run_id=run.run_id,
            summary={
                "total_acceptance_items": 1,
                "passed": 1,
                "failed": 0,
                "uncertain": 0,
                "final_status": "passed",
            },
            item_results=[],
        )


class StubPromptBuilder:
    def __init__(self):
        self.issue = IssueReport(
            issue_id="ISSUE-001",
            severity="high",
            acceptance_item_id="AC-001",
            title="Launch app failed",
            reproduction_steps=["install the app", "launch the app"],
            expected_result="Sunflower visible",
            actual_result="launch flow failed",
            evidence={},
            suspected_causes=["environment or app issue"],
            repair_hint="check launch flow and rerun validation",
        )

    def build_issue_report(self, acceptance_item_id: str, title: str, evidence=None):
        issue = self.issue
        issue.acceptance_item_id = acceptance_item_id
        issue.title = title
        issue.evidence = evidence or {}
        return issue

    def build_repair_prompt(self, issue):
        prompt = f"Fix {issue.acceptance_item_id}: {issue.title}"
        if issue.evidence.get("stderr"):
            prompt += f"\nEvidence stderr: {issue.evidence['stderr']}"
        return prompt


class StubRepairAdapter:
    def __init__(self):
        self.calls = []

    def send_repair_prompt(
        self,
        prompt: str,
        issues: list[dict],
        request_id: str,
        additional_writable_dirs: list[str] | None = None,
    ) -> dict:
        self.calls.append((prompt, issues, request_id, additional_writable_dirs))
        return {
            "status": "queued",
            "target": "cursor",
            "request_id": request_id,
            "issue_count": len(issues),
        }


def test_orchestrator_persists_request_spec_plan_and_judgement(tmp_path):
    request = ValidationRequest(
        request_id="req_001",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubExecutionService(),
        judgement_service=StubJudgementService(),
        prompt_builder=StubPromptBuilder(),
        runs_root=tmp_path,
    )

    result = orchestrator.run_once(request)

    request_path = tmp_path / "req_001" / "request.json"
    spec_path = tmp_path / "req_001" / "spec.json"
    plan_path = tmp_path / "req_001" / "plan.json"
    judgement_path = tmp_path / "req_001" / "loop_01" / "judgement.json"

    assert result["judgement"].summary["final_status"] == "passed"
    assert request_path.exists()
    assert spec_path.exists()
    assert plan_path.exists()
    assert judgement_path.exists()
    assert json.loads(judgement_path.read_text())["summary"]["final_status"] == "passed"


class StubFailedJudgementService:
    def judge(self, spec, run):
        return JudgementResult(
            judgement_id="judge_002",
            run_id=run.run_id,
            summary={
                "total_acceptance_items": 1,
                "passed": 0,
                "failed": 1,
                "uncertain": 0,
                "final_status": "failed",
            },
            item_results=[
                {
                    "acceptance_item_id": "AC-001",
                    "status": "failed",
                    "reason": "execution failed",
                    "linked_case_ids": ["CASE-001"],
                    "confidence": 0.9,
                }
            ],
        )


class StubEnvironmentFailedExecutionService:
    def execute(self, request, plan):
        return ExecutionRun(
            run_id="run_003",
            request_id=request.request_id,
            plan_id=plan.plan_id,
            status="finished",
            device={"kind": "emulator", "serial": "stub-emulator"},
            started_at="2026-03-26T10:00:00+08:00",
            finished_at="2026-03-26T10:01:00+08:00",
            case_results=[
                CaseResult(
                    case_id="CASE-001",
                    status="failed",
                    steps=[{"name": "run maestro flow", "status": "failed"}],
                    artifacts={"stderr": "Operation not permitted"},
                )
            ],
        )


def test_orchestrator_persists_issue_report_and_repair_prompt_for_failed_run(tmp_path):
    request = ValidationRequest(
        request_id="req_002",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubExecutionService(),
        judgement_service=StubFailedJudgementService(),
        prompt_builder=StubPromptBuilder(),
        runs_root=tmp_path,
    )

    result = orchestrator.run_once(request)

    issue_path = tmp_path / "req_002" / "loop_01" / "issues.json"
    prompt_path = tmp_path / "req_002" / "loop_01" / "repair_prompt.md"

    assert result["judgement"].summary["final_status"] == "failed"
    assert issue_path.exists()
    assert prompt_path.exists()
    assert json.loads(issue_path.read_text())[0]["acceptance_item_id"] == "AC-001"
    assert "Fix AC-001" in prompt_path.read_text()


def test_orchestrator_persists_issue_evidence_and_handoff_record(tmp_path):
    request = ValidationRequest(
        request_id="req_004",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )
    repair_adapter = StubRepairAdapter()

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubEnvironmentFailedExecutionService(),
        judgement_service=StubFailedJudgementService(),
        prompt_builder=StubPromptBuilder(),
        repair_adapter=repair_adapter,
        runs_root=tmp_path,
    )

    orchestrator.run_once(request)

    issue_payload = json.loads((tmp_path / "req_004" / "loop_01" / "issues.json").read_text())[0]
    prompt_text = (tmp_path / "req_004" / "loop_01" / "repair_prompt.md").read_text()
    handoff_payload = json.loads((tmp_path / "req_004" / "loop_01" / "repair_handoff.json").read_text())

    assert issue_payload["evidence"]["stderr"] == "Operation not permitted"
    assert "Operation not permitted" in prompt_text
    assert handoff_payload["status"] == "queued"
    assert repair_adapter.calls[0][2] == "req_004"


def test_orchestrator_persists_timeout_details_in_handoff_record(tmp_path):
    request = ValidationRequest(
        request_id="req_007",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )

    class TimeoutRepairAdapter:
        def send_repair_prompt(
            self,
            prompt: str,
            issues: list[dict],
            request_id: str,
            additional_writable_dirs: list[str] | None = None,
        ) -> dict:
            return {
                "status": "failed",
                "target": "codex",
                "request_id": request_id,
                "issue_count": len(issues),
                "stdout": "partial stdout",
                "stderr": "partial stderr",
                "timed_out": True,
                "timeout_seconds": 30,
            }

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubEnvironmentFailedExecutionService(),
        judgement_service=StubFailedJudgementService(),
        prompt_builder=StubPromptBuilder(),
        repair_adapter=TimeoutRepairAdapter(),
        runs_root=tmp_path,
    )

    orchestrator.run_once(request)

    handoff_payload = json.loads((tmp_path / "req_007" / "loop_01" / "repair_handoff.json").read_text())

    assert handoff_payload["status"] == "failed"
    assert handoff_payload["timed_out"] is True
    assert handoff_payload["timeout_seconds"] == 30


def test_orchestrator_persists_loop_summary_file(tmp_path):
    request = ValidationRequest(
        request_id="req_006",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubExecutionService(),
        judgement_service=StubJudgementService(),
        prompt_builder=StubPromptBuilder(),
        runs_root=tmp_path,
    )

    orchestrator.run_once(request, loop_index=1)

    summary_path = tmp_path / "req_006" / "loop_01" / "summary.json"
    summary_payload = json.loads(summary_path.read_text())

    assert summary_path.exists()
    assert summary_payload["loop_index"] == 1
    assert summary_payload["final_status"] == "passed"


def test_orchestrator_marks_environment_failure_in_persisted_issue(tmp_path):
    request = ValidationRequest(
        request_id="req_003",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubEnvironmentFailedExecutionService(),
        judgement_service=StubFailedJudgementService(),
        prompt_builder=StubPromptBuilder(),
        runs_root=tmp_path,
    )

    orchestrator.run_once(request)

    issue_payload = json.loads((tmp_path / "req_003" / "loop_01" / "issues.json").read_text())[0]

    assert issue_payload["failure_type"] == "environment_failure"


def test_orchestrator_persists_second_loop_in_separate_directory(tmp_path):
    request = ValidationRequest(
        request_id="req_005",
        feature_name="sunflower launch",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "App launches"}],
        build={"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": []},
        constraints={"max_loops": 2},
    )

    orchestrator = Orchestrator(
        intake_service=None,
        spec_builder=StubSpecBuilder(),
        test_planner=StubTestPlanner(),
        execution_service=StubExecutionService(),
        judgement_service=StubJudgementService(),
        prompt_builder=StubPromptBuilder(),
        runs_root=tmp_path,
    )

    orchestrator.run_once(request, loop_index=1)
    orchestrator.run_once(request, loop_index=2)

    assert (tmp_path / "req_005" / "loop_01" / "judgement.json").exists()
    assert (tmp_path / "req_005" / "loop_02" / "judgement.json").exists()
