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
