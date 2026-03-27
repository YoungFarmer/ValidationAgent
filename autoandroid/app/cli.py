import argparse
import json
from pathlib import Path

from autoandroid.app.integrations.adb_runner import AdbRunner
from autoandroid.app.integrations.codex_adapter import CodexAdapter
from autoandroid.app.integrations.gradle_build_adapter import GradleBuildAdapter
from autoandroid.app.integrations.maestro_runner import MaestroRunner
from autoandroid.app.orchestrator import Orchestrator
from autoandroid.app.rules.failure_classifier import FailureClassifier
from autoandroid.app.services.execution_service import ExecutionService
from autoandroid.app.services.intake_service import IntakeService
from autoandroid.app.services.judgement_service import JudgementService
from autoandroid.app.services.prompt_builder import PromptBuilder
from autoandroid.app.services.repair_loop_manager import RepairLoopManager
from autoandroid.app.services.spec_builder import SpecBuilder
from autoandroid.app.services.test_planner import TestPlanner


def build_parser():
    parser = argparse.ArgumentParser(prog="autoandroid")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_request = subparsers.add_parser("run-request")
    run_request.add_argument("request_path")
    run_request.add_argument("--runs-root", dest="runs_root")

    run_loop = subparsers.add_parser("run-loop")
    run_loop.add_argument("request_path")
    run_loop.add_argument("--runs-root", dest="runs_root")
    return parser


def create_default_orchestrator(runs_root=None):
    resolved_runs_root = runs_root or "autoandroid/runs"
    return Orchestrator(
        intake_service=None,
        spec_builder=SpecBuilder(llm_provider=None),
        test_planner=TestPlanner(),
        execution_service=ExecutionService(maestro_runner=MaestroRunner(), adb_runner=AdbRunner()),
        judgement_service=JudgementService(),
        prompt_builder=PromptBuilder(),
        failure_classifier=FailureClassifier(),
        repair_adapter=CodexAdapter(
            workspace_root=".",
            output_last_message_path=f"{resolved_runs_root}/codex-last-message.txt",
        ),
        runs_root=resolved_runs_root,
    )


def _read_json_file(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _read_text_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text()


def _collect_loop_trace(runs_root: Path, request_id: str, completed_loops: int) -> list[dict]:
    request_root = runs_root / request_id
    trace = []
    for loop_index in range(1, completed_loops + 1):
        loop_dir = request_root / f"loop_{loop_index:02d}"
        issues = _read_json_file(loop_dir / "issues.json") or []
        entry = {
            "loop_index": loop_index,
            "summary": _read_json_file(loop_dir / "summary.json") or {},
            "judgement_status": (_read_json_file(loop_dir / "judgement.json") or {})
            .get("summary", {})
            .get("final_status", "unknown"),
            "failure_type": issues[0].get("failure_type", "unknown") if issues else "unknown",
            "issues": issues,
            "repair_prompt": _read_text_file(loop_dir / "repair_prompt.md"),
        }
        handoff = _read_json_file(loop_dir / "repair_handoff.json")
        rebuild = _read_json_file(loop_dir / "rebuild.json")
        if handoff:
            entry["repair_handoff"] = handoff
        if rebuild:
            entry["rebuild"] = rebuild
        trace.append(entry)
    return trace


def _augment_repair_prompt(prompt: str, request) -> str:
    build = getattr(request, "build", {}) or {}
    context_lines = []
    if build.get("project_dir"):
        context_lines.append(f"Project directory: {build['project_dir']}")
    if build.get("ref"):
        context_lines.append(f"APK path: {build['ref']}")
    if build.get("app_id"):
        context_lines.append(f"App id: {build['app_id']}")
    if not context_lines:
        return prompt
    return prompt.rstrip() + "\n\nTarget context:\n" + "\n".join(context_lines) + "\n"


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run-request":
        request = IntakeService().load_request(args.request_path)
        result = create_default_orchestrator(runs_root=args.runs_root).run_once(request)
        print(result["judgement"].summary["final_status"])
        return 0
    if args.command == "run-loop":
        request = IntakeService().load_request(args.request_path)
        orchestrator = create_default_orchestrator(runs_root=args.runs_root)
        loop_manager = RepairLoopManager(stop_conditions=None)
        repair_adapter = orchestrator._repair_adapter
        orchestrator._repair_adapter = None
        active_loop = {"index": 1}

        class PersistingRepairAdapter:
            def __init__(self, wrapped_adapter, runs_root, request_id, active_loop_ref):
                self._wrapped_adapter = wrapped_adapter
                self._runs_root = runs_root
                self._request_id = request_id
                self._active_loop_ref = active_loop_ref

            def send_repair_prompt(
                self,
                prompt: str,
                issues: list[dict],
                request_id: str,
                additional_writable_dirs: list[str] | None = None,
            ) -> dict:
                result = self._wrapped_adapter.send_repair_prompt(
                    prompt,
                    issues,
                    request_id,
                    additional_writable_dirs=additional_writable_dirs,
                )
                loop_dir = self._runs_root / self._request_id / f"loop_{self._active_loop_ref['index']:02d}"
                loop_dir.mkdir(parents=True, exist_ok=True)
                (loop_dir / "repair_handoff.json").write_text(json.dumps(result, indent=2))
                return result

        class PersistingBuildAdapter:
            def __init__(self, wrapped_adapter, runs_root, request_id, active_loop_ref):
                self._wrapped_adapter = wrapped_adapter
                self._runs_root = runs_root
                self._request_id = request_id
                self._active_loop_ref = active_loop_ref

            def rebuild(self, request) -> dict:
                result = self._wrapped_adapter.rebuild(request)
                loop_dir = self._runs_root / self._request_id / f"loop_{self._active_loop_ref['index']:02d}"
                loop_dir.mkdir(parents=True, exist_ok=True)
                (loop_dir / "rebuild.json").write_text(json.dumps(result, indent=2))
                return result

        persisting_repair_adapter = PersistingRepairAdapter(
            repair_adapter,
            orchestrator._runs_root,
            request.request_id,
            active_loop,
        )
        build_adapter = PersistingBuildAdapter(
            GradleBuildAdapter(),
            orchestrator._runs_root,
            request.request_id,
            active_loop,
        )

        def run_validation(loop_index: int):
            active_loop["index"] = loop_index
            result = orchestrator.run_once(request, loop_index=loop_index)
            issues = []
            repair_prompt = ""
            loop_dir = orchestrator._runs_root / request.request_id / f"loop_{loop_index:02d}"
            if result["judgement"].summary["final_status"] == "failed":
                issues_path = loop_dir / "issues.json"
                prompt_path = loop_dir / "repair_prompt.md"
                if issues_path.exists():
                    issues = json.loads(issues_path.read_text())
                if prompt_path.exists():
                    repair_prompt = prompt_path.read_text()
            repair_prompt = _augment_repair_prompt(repair_prompt, request)
            failure_type = issues[0].get("failure_type", "unknown") if issues else "unknown"
            return {
                "judgement_status": result["judgement"].summary["final_status"],
                "failure_type": failure_type,
                "issues": issues,
                "repair_prompt": repair_prompt,
            }

        loop_result = loop_manager.run_loop(
            request=request,
            run_validation=run_validation,
            repair_adapter=persisting_repair_adapter,
            build_adapter=build_adapter,
        )
        trace_path = orchestrator._runs_root / request.request_id / "loop_trace.json"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(
            json.dumps(
                {
                    "request_id": request.request_id,
                    "final_status": loop_result.get("final_status"),
                    "completed_loops": loop_result.get("completed_loops"),
                    "reason": loop_result.get("reason"),
                    "loops": _collect_loop_trace(
                        orchestrator._runs_root,
                        request.request_id,
                        loop_result.get("completed_loops", 0),
                    ),
                    "final_summary": loop_result,
                },
                indent=2,
            )
        )
        print(loop_result["final_status"])
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
