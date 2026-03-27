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
