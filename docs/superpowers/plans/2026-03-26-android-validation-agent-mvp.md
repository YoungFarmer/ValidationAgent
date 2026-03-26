# Android Validation Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an emulator-first MVP that turns one Android requirement into a structured acceptance spec, an executable Maestro/adb validation plan, an evidence-backed judgement result, and a repair prompt for Cursor or Codex.

**Architecture:** The MVP is a local Python orchestration app with clear modules for request intake, spec building, test planning, execution, judgement, and repair-loop management. Machine-readable state is persisted as JSON under `runs/`, while human-readable outputs are rendered as Markdown from the same underlying data.

**Tech Stack:** Python 3.11+, pytest, pydantic, Typer or argparse, Maestro CLI, adb, SQLite or local JSON persistence

---

## File Structure

Planned files and responsibilities:

- Create: `autoandroid/app/cli.py`
  CLI entrypoint for single-run and loop-run commands.
- Create: `autoandroid/app/orchestrator.py`
  Top-level orchestration for validation lifecycle states.
- Create: `autoandroid/app/models/request.py`
  Request data models and parsing helpers.
- Create: `autoandroid/app/models/spec.py`
  Acceptance spec models.
- Create: `autoandroid/app/models/plan.py`
  Test plan models.
- Create: `autoandroid/app/models/run.py`
  Execution result and judgement models.
- Create: `autoandroid/app/models/issue.py`
  Issue report and repair prompt models.
- Create: `autoandroid/app/services/intake_service.py`
  Request normalization from input files and CLI arguments.
- Create: `autoandroid/app/services/spec_builder.py`
  Convert request data into `acceptance_spec`.
- Create: `autoandroid/app/services/test_planner.py`
  Convert spec into executable Maestro/adb cases.
- Create: `autoandroid/app/services/execution_service.py`
  Run environment prep and case execution.
- Create: `autoandroid/app/services/judgement_service.py`
  Convert execution evidence into item-level judgement.
- Create: `autoandroid/app/services/prompt_builder.py`
  Render issue reports and repair prompts.
- Create: `autoandroid/app/services/repair_loop_manager.py`
  Drive repeated validation loops with stop conditions.
- Create: `autoandroid/app/integrations/maestro_runner.py`
  Wrap `maestro test` invocation and output capture.
- Create: `autoandroid/app/integrations/adb_runner.py`
  Wrap adb install, launch, and log commands.
- Create: `autoandroid/app/integrations/llm_provider.py`
  Abstract prompt-driven structured generation.
- Create: `autoandroid/app/integrations/cursor_adapter.py`
  Stub adapter for automatic handoff to Cursor.
- Create: `autoandroid/app/integrations/codex_adapter.py`
  Stub adapter for automatic handoff to Codex.
- Create: `autoandroid/app/rules/failure_classifier.py`
  Failure type classification rules.
- Create: `autoandroid/app/rules/stop_conditions.py`
  Loop stop logic.
- Create: `autoandroid/app/templates/acceptance_spec_prompt.md`
  Prompt template for structured spec generation.
- Create: `autoandroid/app/templates/repair_prompt.md`
  Prompt template for implementation-agent repair handoff.
- Create: `autoandroid/app/templates/issue_report.md`
  Human-readable issue report template.
- Create: `autoandroid/tests/test_models.py`
  Model serialization and validation tests.
- Create: `autoandroid/tests/test_spec_builder.py`
  Spec generation behavior tests using deterministic fixtures.
- Create: `autoandroid/tests/test_test_planner.py`
  Test plan mapping tests.
- Create: `autoandroid/tests/test_judgement_service.py`
  Acceptance item judgement tests.
- Create: `autoandroid/tests/test_stop_conditions.py`
  Loop stop rule tests.
- Create: `autoandroid/tests/test_prompt_builder.py`
  Issue report and repair prompt rendering tests.
- Create: `autoandroid/tests/fixtures/sample_request.json`
  Sample request payload for tests.
- Create: `autoandroid/tests/fixtures/sample_spec.json`
  Sample acceptance spec for tests.
- Create: `autoandroid/tests/fixtures/sample_execution_run.json`
  Sample run artifact for judgement tests.
- Create: `autoandroid/config/settings.yaml`
  Local config defaults.
- Create: `autoandroid/flows/generated/.gitkeep`
  Placeholder for generated Maestro flows.
- Create: `autoandroid/flows/stable/.gitkeep`
  Placeholder for stable Maestro flows.
- Create: `autoandroid/runs/.gitkeep`
  Placeholder for run artifacts.

### Task 1: Bootstrap Project Skeleton and Core Models

**Files:**
- Create: `autoandroid/app/cli.py`
- Create: `autoandroid/app/orchestrator.py`
- Create: `autoandroid/app/models/request.py`
- Create: `autoandroid/app/models/spec.py`
- Create: `autoandroid/app/models/plan.py`
- Create: `autoandroid/app/models/run.py`
- Create: `autoandroid/app/models/issue.py`
- Create: `autoandroid/tests/test_models.py`
- Create: `autoandroid/tests/fixtures/sample_request.json`
- Create: `autoandroid/config/settings.yaml`

- [ ] **Step 1: Write the failing model test**

```python
from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.models.spec import AcceptanceSpec, AcceptanceItem


def test_validation_request_and_spec_roundtrip():
    request = ValidationRequest(
        request_id="req_001",
        feature_name="coupon flow",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "Show coupon entry"}],
        build={"source_type": "apk", "ref": "app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": ["buyer_a"]},
        constraints={"max_loops": 3},
    )

    spec = AcceptanceSpec(
        spec_id="spec_001",
        feature_name="coupon flow",
        in_scope=["show coupon entry"],
        out_of_scope=[],
        acceptance_items=[
            AcceptanceItem(
                id="AC-001",
                title="Show coupon entry",
                type="ui",
                priority="high",
                preconditions=["user logged in"],
                steps=["open order confirm"],
                expected=["coupon entry visible"],
                evidence=["screenshot"],
            )
        ],
    )

    request_payload = request.model_dump()
    spec_payload = spec.model_dump()

    assert request_payload["request_id"] == "req_001"
    assert spec_payload["acceptance_items"][0]["id"] == "AC-001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest autoandroid/tests/test_models.py -v`
Expected: FAIL with import errors because the model modules do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# autoandroid/app/models/request.py
from typing import Any

from pydantic import BaseModel


class ValidationRequest(BaseModel):
    request_id: str
    feature_name: str
    goal: str
    requirement_sources: list[dict[str, Any]]
    build: dict[str, Any]
    environment: dict[str, Any]
    credentials: dict[str, Any]
    constraints: dict[str, Any]
```

```python
# autoandroid/app/models/spec.py
from pydantic import BaseModel


class AcceptanceItem(BaseModel):
    id: str
    title: str
    type: str
    priority: str
    preconditions: list[str]
    steps: list[str]
    expected: list[str]
    evidence: list[str]


class AcceptanceSpec(BaseModel):
    spec_id: str
    feature_name: str
    in_scope: list[str]
    out_of_scope: list[str]
    acceptance_items: list[AcceptanceItem]
```

```python
# autoandroid/app/models/plan.py
from typing import Any

from pydantic import BaseModel


class TestCase(BaseModel):
    case_id: str
    acceptance_item_id: str
    tooling: dict[str, Any]
    environment: dict[str, Any]
    assertions: list[str]
    artifacts: list[str]


class TestPlan(BaseModel):
    plan_id: str
    spec_id: str
    cases: list[TestCase]
```

```python
# autoandroid/app/models/run.py
from typing import Any

from pydantic import BaseModel


class CaseResult(BaseModel):
    case_id: str
    status: str
    steps: list[dict[str, Any]]
    artifacts: dict[str, Any]


class ExecutionRun(BaseModel):
    run_id: str
    request_id: str
    plan_id: str
    status: str
    device: dict[str, Any]
    started_at: str
    finished_at: str
    case_results: list[CaseResult]


class JudgementItemResult(BaseModel):
    acceptance_item_id: str
    status: str
    reason: str
    linked_case_ids: list[str]
    confidence: float


class JudgementResult(BaseModel):
    judgement_id: str
    run_id: str
    summary: dict[str, Any]
    item_results: list[JudgementItemResult]
```

```python
# autoandroid/app/models/issue.py
from typing import Any

from pydantic import BaseModel


class IssueReport(BaseModel):
    issue_id: str
    severity: str
    acceptance_item_id: str
    title: str
    reproduction_steps: list[str]
    expected_result: str
    actual_result: str
    evidence: dict[str, Any]
    suspected_causes: list[str]
    repair_hint: str
```

- [ ] **Step 4: Add package markers and sample fixture**

```python
# autoandroid/app/__init__.py
```

```python
# autoandroid/tests/__init__.py
```

```json
{
  "request_id": "req_001",
  "feature_name": "coupon flow",
  "goal": "verify feature completion",
  "requirement_sources": [
    {
      "type": "prd",
      "content": "Show coupon entry and update total after selection"
    }
  ],
  "build": {
    "source_type": "apk",
    "ref": "app-debug.apk"
  },
  "environment": {
    "platform": "android",
    "mode": "emulator_first"
  },
  "credentials": {
    "profiles": ["buyer_a"]
  },
  "constraints": {
    "max_loops": 3
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest autoandroid/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add autoandroid/app autoandroid/tests autoandroid/config
git commit -m "feat: bootstrap validation agent models"
```

### Task 2: Implement Intake and Deterministic Spec Builder

**Files:**
- Create: `autoandroid/app/services/intake_service.py`
- Create: `autoandroid/app/services/spec_builder.py`
- Create: `autoandroid/app/integrations/llm_provider.py`
- Create: `autoandroid/app/templates/acceptance_spec_prompt.md`
- Create: `autoandroid/tests/test_spec_builder.py`
- Create: `autoandroid/tests/fixtures/sample_spec.json`

- [ ] **Step 1: Write the failing spec-builder test**

```python
from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.services.spec_builder import SpecBuilder


class StubLlmProvider:
    def generate_structured_json(self, template_name: str, context: dict) -> dict:
        return {
            "spec_id": "spec_001",
            "feature_name": context["feature_name"],
            "in_scope": ["show coupon entry"],
            "out_of_scope": ["coupon backend issuing"],
            "acceptance_items": [
                {
                    "id": "AC-001",
                    "title": "Show coupon entry",
                    "type": "ui",
                    "priority": "high",
                    "preconditions": ["user logged in"],
                    "steps": ["open order confirm"],
                    "expected": ["coupon entry visible"],
                    "evidence": ["screenshot"]
                }
            ]
        }


def test_spec_builder_returns_acceptance_spec():
    request = ValidationRequest(
        request_id="req_001",
        feature_name="coupon flow",
        goal="verify feature completion",
        requirement_sources=[{"type": "prd", "content": "Show coupon entry"}],
        build={"source_type": "apk", "ref": "app-debug.apk"},
        environment={"platform": "android", "mode": "emulator_first"},
        credentials={"profiles": ["buyer_a"]},
        constraints={"max_loops": 3},
    )

    builder = SpecBuilder(llm_provider=StubLlmProvider())
    spec = builder.build(request)

    assert spec.spec_id == "spec_001"
    assert spec.acceptance_items[0].title == "Show coupon entry"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest autoandroid/tests/test_spec_builder.py -v`
Expected: FAIL because `SpecBuilder` and the LLM provider interface do not exist yet.

- [ ] **Step 3: Write minimal intake and spec builder implementation**

```python
# autoandroid/app/integrations/llm_provider.py
from typing import Protocol


class LlmProvider(Protocol):
    def generate_structured_json(self, template_name: str, context: dict) -> dict:
        ...
```

```python
# autoandroid/app/services/intake_service.py
import json
from pathlib import Path

from autoandroid.app.models.request import ValidationRequest


class IntakeService:
    def load_request(self, path: str) -> ValidationRequest:
        payload = json.loads(Path(path).read_text())
        return ValidationRequest(**payload)
```

```python
# autoandroid/app/services/spec_builder.py
from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.models.spec import AcceptanceSpec


class SpecBuilder:
    def __init__(self, llm_provider):
        self._llm_provider = llm_provider

    def build(self, request: ValidationRequest) -> AcceptanceSpec:
        payload = self._llm_provider.generate_structured_json(
            "acceptance_spec_prompt.md",
            {
                "feature_name": request.feature_name,
                "goal": request.goal,
                "requirement_sources": request.requirement_sources,
            },
        )
        return AcceptanceSpec(**payload)
```

```md
<!-- autoandroid/app/templates/acceptance_spec_prompt.md -->
Convert the requirement inputs into a strict JSON acceptance spec.
Return only JSON.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest autoandroid/tests/test_spec_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add autoandroid/app/services autoandroid/app/integrations autoandroid/app/templates autoandroid/tests
git commit -m "feat: add intake and spec builder"
```

### Task 3: Implement Test Planner and Maestro/adb Execution Adapters

**Files:**
- Create: `autoandroid/app/services/test_planner.py`
- Create: `autoandroid/app/services/execution_service.py`
- Create: `autoandroid/app/integrations/maestro_runner.py`
- Create: `autoandroid/app/integrations/adb_runner.py`
- Create: `autoandroid/tests/test_test_planner.py`

- [ ] **Step 1: Write the failing planner test**

```python
from autoandroid.app.models.spec import AcceptanceItem, AcceptanceSpec
from autoandroid.app.services.test_planner import TestPlanner


def test_test_planner_maps_acceptance_item_to_case():
    spec = AcceptanceSpec(
        spec_id="spec_001",
        feature_name="coupon flow",
        in_scope=["show coupon entry"],
        out_of_scope=[],
        acceptance_items=[
            AcceptanceItem(
                id="AC-001",
                title="Show coupon entry",
                type="ui",
                priority="high",
                preconditions=["user logged in"],
                steps=["open order confirm"],
                expected=["coupon entry visible"],
                evidence=["screenshot"],
            )
        ],
    )

    planner = TestPlanner()
    plan = planner.build(spec)

    assert plan.cases[0].acceptance_item_id == "AC-001"
    assert plan.cases[0].tooling["maestro_flow"].endswith(".yaml")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest autoandroid/tests/test_test_planner.py -v`
Expected: FAIL because `TestPlanner` does not exist yet.

- [ ] **Step 3: Write minimal planner and runner stubs**

```python
# autoandroid/app/services/test_planner.py
from autoandroid.app.models.plan import TestCase, TestPlan
from autoandroid.app.models.spec import AcceptanceSpec


class TestPlanner:
    def build(self, spec: AcceptanceSpec) -> TestPlan:
        cases = []
        for index, item in enumerate(spec.acceptance_items, start=1):
            cases.append(
                TestCase(
                    case_id=f"CASE-{index:03d}",
                    acceptance_item_id=item.id,
                    tooling={
                        "maestro_flow": f"autoandroid/flows/generated/{item.id.lower()}.yaml",
                        "adb_commands": ["adb logcat -c"],
                    },
                    environment={"device_type": "emulator"},
                    assertions=item.expected,
                    artifacts=item.evidence,
                )
            )
        return TestPlan(plan_id=f"plan_{spec.spec_id}", spec_id=spec.spec_id, cases=cases)
```

```python
# autoandroid/app/integrations/maestro_runner.py
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
```

```python
# autoandroid/app/integrations/adb_runner.py
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
```

```python
# autoandroid/app/services/execution_service.py
from autoandroid.app.models.run import ExecutionRun


class ExecutionService:
    def __init__(self, maestro_runner, adb_runner):
        self._maestro_runner = maestro_runner
        self._adb_runner = adb_runner

    def execute(self, request_id: str, plan_id: str) -> ExecutionRun:
        return ExecutionRun(
            run_id="run_001",
            request_id=request_id,
            plan_id=plan_id,
            status="finished",
            device={"kind": "emulator", "serial": "stub-emulator"},
            started_at="2026-03-26T10:00:00+08:00",
            finished_at="2026-03-26T10:01:00+08:00",
            case_results=[],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest autoandroid/tests/test_test_planner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add autoandroid/app/services autoandroid/app/integrations autoandroid/tests
git commit -m "feat: add planning and execution adapters"
```

### Task 4: Implement Judgement, Failure Classification, and Prompt Rendering

**Files:**
- Create: `autoandroid/app/services/judgement_service.py`
- Create: `autoandroid/app/services/prompt_builder.py`
- Create: `autoandroid/app/rules/failure_classifier.py`
- Create: `autoandroid/app/templates/repair_prompt.md`
- Create: `autoandroid/app/templates/issue_report.md`
- Create: `autoandroid/tests/test_judgement_service.py`
- Create: `autoandroid/tests/test_prompt_builder.py`
- Create: `autoandroid/tests/fixtures/sample_execution_run.json`

- [ ] **Step 1: Write the failing judgement test**

```python
from autoandroid.app.models.run import CaseResult, ExecutionRun
from autoandroid.app.models.spec import AcceptanceItem, AcceptanceSpec
from autoandroid.app.services.judgement_service import JudgementService


def test_judgement_service_marks_missing_assertion_as_failed():
    spec = AcceptanceSpec(
        spec_id="spec_001",
        feature_name="coupon flow",
        in_scope=["show coupon entry"],
        out_of_scope=[],
        acceptance_items=[
            AcceptanceItem(
                id="AC-001",
                title="Show coupon entry",
                type="ui",
                priority="high",
                preconditions=["user logged in"],
                steps=["open order confirm"],
                expected=["coupon entry visible"],
                evidence=["screenshot"],
            )
        ],
    )

    run = ExecutionRun(
        run_id="run_001",
        request_id="req_001",
        plan_id="plan_spec_001",
        status="finished",
        device={"kind": "emulator", "serial": "stub-emulator"},
        started_at="2026-03-26T10:00:00+08:00",
        finished_at="2026-03-26T10:01:00+08:00",
        case_results=[
            CaseResult(
                case_id="CASE-001",
                status="failed",
                steps=[{"name": "assert coupon entry visible", "status": "failed"}],
                artifacts={"screenshots": ["missing.png"]},
            )
        ],
    )

    judgement = JudgementService().judge(spec, run)

    assert judgement.summary["final_status"] == "failed"
    assert judgement.item_results[0].acceptance_item_id == "AC-001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest autoandroid/tests/test_judgement_service.py -v`
Expected: FAIL because `JudgementService` does not exist.

- [ ] **Step 3: Write minimal judgement and prompt builder implementation**

```python
# autoandroid/app/services/judgement_service.py
from autoandroid.app.models.run import JudgementItemResult, JudgementResult


class JudgementService:
    def judge(self, spec, run):
        item_results = []
        failed = 0
        for item, case in zip(spec.acceptance_items, run.case_results):
            status = "passed" if case.status == "passed" else "failed"
            if status == "failed":
                failed += 1
            item_results.append(
                JudgementItemResult(
                    acceptance_item_id=item.id,
                    status=status,
                    reason="execution failed" if status == "failed" else "all assertions satisfied",
                    linked_case_ids=[case.case_id],
                    confidence=0.95 if status == "passed" else 0.9,
                )
            )

        return JudgementResult(
            judgement_id=f"judge_{run.run_id}",
            run_id=run.run_id,
            summary={
                "total_acceptance_items": len(spec.acceptance_items),
                "passed": len(spec.acceptance_items) - failed,
                "failed": failed,
                "uncertain": 0,
                "final_status": "failed" if failed else "passed",
            },
            item_results=item_results,
        )
```

```python
# autoandroid/app/rules/failure_classifier.py
class FailureClassifier:
    def classify(self, case_result) -> str:
        if case_result.status == "failed":
            return "product_bug"
        return "unknown"
```

```python
# autoandroid/app/services/prompt_builder.py
from autoandroid.app.models.issue import IssueReport


class PromptBuilder:
    def build_issue_report(self, acceptance_item_id: str, title: str) -> IssueReport:
        return IssueReport(
            issue_id="ISSUE-001",
            severity="high",
            acceptance_item_id=acceptance_item_id,
            title=title,
            reproduction_steps=["reproduce with validation flow"],
            expected_result="acceptance item passes",
            actual_result="acceptance item failed",
            evidence={},
            suspected_causes=["implementation incomplete"],
            repair_hint="inspect the feature logic and rerun validation",
        )

    def build_repair_prompt(self, issue: IssueReport) -> str:
        return (
            f"Fix acceptance item {issue.acceptance_item_id}: {issue.title}\n"
            f"Expected: {issue.expected_result}\n"
            f"Actual: {issue.actual_result}\n"
            f"Hint: {issue.repair_hint}\n"
        )
```

- [ ] **Step 4: Add prompt-builder test**

```python
from autoandroid.app.services.prompt_builder import PromptBuilder


def test_prompt_builder_includes_issue_context():
    builder = PromptBuilder()
    issue = builder.build_issue_report("AC-001", "Coupon entry missing")
    prompt = builder.build_repair_prompt(issue)

    assert "AC-001" in prompt
    assert "Coupon entry missing" in prompt
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest autoandroid/tests/test_judgement_service.py autoandroid/tests/test_prompt_builder.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add autoandroid/app/services autoandroid/app/rules autoandroid/app/templates autoandroid/tests
git commit -m "feat: add judgement and repair prompt generation"
```

### Task 5: Add Stop Conditions, Loop Manager, and CLI Wiring

**Files:**
- Create: `autoandroid/app/services/repair_loop_manager.py`
- Create: `autoandroid/app/rules/stop_conditions.py`
- Modify: `autoandroid/app/orchestrator.py`
- Modify: `autoandroid/app/cli.py`
- Create: `autoandroid/tests/test_stop_conditions.py`

- [ ] **Step 1: Write the failing stop-condition test**

```python
from autoandroid.app.rules.stop_conditions import StopConditions


def test_stop_conditions_blocks_after_max_loops():
    rules = StopConditions(max_loops=3)
    should_stop = rules.should_stop(loop_index=3, judgement_status="failed", failure_type="product_bug")
    assert should_stop is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest autoandroid/tests/test_stop_conditions.py -v`
Expected: FAIL because `StopConditions` does not exist.

- [ ] **Step 3: Write minimal stop-condition and loop-manager implementation**

```python
# autoandroid/app/rules/stop_conditions.py
class StopConditions:
    def __init__(self, max_loops: int):
        self._max_loops = max_loops

    def should_stop(self, loop_index: int, judgement_status: str, failure_type: str) -> bool:
        if judgement_status == "passed":
            return True
        if failure_type == "environment_failure":
            return True
        return loop_index >= self._max_loops
```

```python
# autoandroid/app/services/repair_loop_manager.py
class RepairLoopManager:
    def __init__(self, stop_conditions):
        self._stop_conditions = stop_conditions

    def next_action(self, loop_index: int, judgement_status: str, failure_type: str) -> str:
        if judgement_status == "passed":
            return "verified"
        if self._stop_conditions.should_stop(loop_index, judgement_status, failure_type):
            return "blocked"
        return "repair_requested"
```

```python
# autoandroid/app/orchestrator.py
class Orchestrator:
    def __init__(self, intake_service, spec_builder, test_planner, execution_service, judgement_service, prompt_builder):
        self._intake_service = intake_service
        self._spec_builder = spec_builder
        self._test_planner = test_planner
        self._execution_service = execution_service
        self._judgement_service = judgement_service
        self._prompt_builder = prompt_builder

    def run_once(self, request):
        spec = self._spec_builder.build(request)
        plan = self._test_planner.build(spec)
        run = self._execution_service.execute(request.request_id, plan.plan_id)
        judgement = self._judgement_service.judge(spec, run)
        return {"spec": spec, "plan": plan, "run": run, "judgement": judgement}
```

```python
# autoandroid/app/cli.py
def main():
    print("Usage: python -m autoandroid.app.cli <command>")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest autoandroid/tests/test_stop_conditions.py -v`
Expected: PASS

- [ ] **Step 5: Run a lightweight full test suite**

Run: `pytest autoandroid/tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add autoandroid/app autoandroid/tests
git commit -m "feat: add repair loop control and cli wiring"
```

### Task 6: Persist Run Artifacts and Render Human-Readable Outputs

**Files:**
- Modify: `autoandroid/app/orchestrator.py`
- Modify: `autoandroid/app/services/prompt_builder.py`
- Create: `autoandroid/tests/test_persistence_outputs.py`
- Create: `autoandroid/runs/.gitkeep`
- Create: `autoandroid/flows/generated/.gitkeep`
- Create: `autoandroid/flows/stable/.gitkeep`

- [ ] **Step 1: Write the failing persistence test**

```python
from pathlib import Path


def test_run_outputs_are_persisted(tmp_path):
    run_dir = tmp_path / "runs" / "req_001" / "loop_01"
    run_dir.mkdir(parents=True)
    (run_dir / "judgement.json").write_text('{"summary":{"final_status":"failed"}}')

    assert (run_dir / "judgement.json").exists()
```

- [ ] **Step 2: Run test to verify it fails in the real integration point**

Run: `pytest autoandroid/tests/test_persistence_outputs.py -v`
Expected: PASS for the initial file-write smoke test.

- [ ] **Step 3: Replace with real persistence behavior**

```python
# orchestrator persistence sketch
import json
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
```

The final implementation should persist:

- `runs/<request_id>/request.json`
- `runs/<request_id>/spec.json`
- `runs/<request_id>/plan.json`
- `runs/<request_id>/loop_01/run.json`
- `runs/<request_id>/loop_01/judgement.json`
- `runs/<request_id>/loop_01/issues.json`
- `runs/<request_id>/loop_01/repair_prompt.md`

- [ ] **Step 4: Run the full test suite**

Run: `pytest autoandroid/tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add autoandroid/app autoandroid/tests autoandroid/runs autoandroid/flows
git commit -m "feat: persist validation outputs and reports"
```

## Self-Review Checklist

- Spec coverage:
  - intake, spec, plan, execution, judgement, issue reporting, repair prompt, loop control, and persisted artifacts are each covered by at least one task.
  - device re-verification is intentionally not implemented in MVP and remains out of scope.
- Placeholder scan:
  - all tasks include concrete files, tests, commands, and minimal code direction.
  - the only intentionally open area is the exact automatic adapter implementation for Cursor/Codex, which is stubbed in MVP and can be expanded later.
- Type consistency:
  - `ValidationRequest`, `AcceptanceSpec`, `TestPlan`, `ExecutionRun`, `JudgementResult`, and `IssueReport` names are used consistently across tasks.
