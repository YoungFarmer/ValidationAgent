import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from autoandroid.app.rules.failure_classifier import FailureClassifier


class Orchestrator:
    def __init__(
        self,
        intake_service,
        spec_builder,
        test_planner,
        execution_service,
        judgement_service,
        prompt_builder,
        failure_classifier=None,
        repair_adapter=None,
        runs_root="autoandroid/runs",
    ):
        self._intake_service = intake_service
        self._spec_builder = spec_builder
        self._test_planner = test_planner
        self._execution_service = execution_service
        self._judgement_service = judgement_service
        self._prompt_builder = prompt_builder
        self._failure_classifier = failure_classifier or FailureClassifier()
        self._repair_adapter = repair_adapter
        self._runs_root = Path(runs_root)

    def run_once(self, request, loop_index=1):
        request_root = self._runs_root / request.request_id
        loop_dir = request_root / f"loop_{loop_index:02d}"
        spec = self._spec_builder.build(request)
        plan = self._test_planner.build(spec)
        run = self._execution_service.execute(request, plan)
        judgement = self._judgement_service.judge(spec, run)

        self._write_json(request_root / "request.json", request)
        self._write_json(request_root / "spec.json", spec)
        self._write_json(request_root / "plan.json", plan)
        self._write_json(loop_dir / "run.json", run)
        self._write_json(loop_dir / "judgement.json", judgement)
        self._write_json(
            loop_dir / "summary.json",
            {
                "request_id": request.request_id,
                "loop_index": loop_index,
                "final_status": judgement.summary.get("final_status"),
                "run_id": run.run_id,
                "plan_id": plan.plan_id,
            },
        )
        if judgement.summary.get("final_status") == "failed":
            issues = self._build_issues(judgement, run)
            repair_prompt = self._build_repair_prompt(issues)
            self._write_json(loop_dir / "issues.json", issues)
            loop_dir.mkdir(parents=True, exist_ok=True)
            (loop_dir / "repair_prompt.md").write_text(repair_prompt)
            if self._repair_adapter is not None:
                handoff = self._repair_adapter.send_repair_prompt(
                    repair_prompt,
                    issues,
                    request.request_id,
                    additional_writable_dirs=[request.build.get("project_dir", "")],
                )
                self._write_json(loop_dir / "repair_handoff.json", handoff)

        return {"spec": spec, "plan": plan, "run": run, "judgement": judgement}

    def _write_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_dataclass(payload):
            serializable = asdict(payload)
        else:
            serializable = payload
        path.write_text(json.dumps(serializable, indent=2))

    def _build_issues(self, judgement, run):
        issues = []
        case_results_by_id = {case.case_id: case for case in run.case_results}
        for item_result in judgement.item_results:
            if isinstance(item_result, dict):
                acceptance_item_id = item_result["acceptance_item_id"]
                title = item_result["reason"]
                linked_case_ids = item_result.get("linked_case_ids", [])
            else:
                acceptance_item_id = item_result.acceptance_item_id
                title = item_result.reason
                linked_case_ids = item_result.linked_case_ids
            evidence = {}
            if linked_case_ids:
                case_result = case_results_by_id.get(linked_case_ids[0])
                if case_result is not None:
                    evidence = case_result.artifacts
            issue = self._prompt_builder.build_issue_report(acceptance_item_id, title, evidence=evidence)
            issue_payload = asdict(issue) if is_dataclass(issue) else issue
            if self._failure_classifier and linked_case_ids:
                case_result = case_results_by_id.get(linked_case_ids[0])
                if case_result is not None:
                    issue_payload["failure_type"] = self._failure_classifier.classify(case_result)
            issues.append(issue_payload)
        return issues

    def _build_repair_prompt(self, issues: list[dict]) -> str:
        prompt_sections = []
        for issue_payload in issues:
            issue = self._prompt_builder.build_issue_report(
                issue_payload["acceptance_item_id"],
                issue_payload["title"],
                evidence=issue_payload.get("evidence", {}),
            )
            prompt_sections.append(self._prompt_builder.build_repair_prompt(issue))
        return "\n".join(prompt_sections).strip() + "\n"
