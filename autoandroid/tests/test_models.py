from dataclasses import asdict

from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.models.spec import AcceptanceItem, AcceptanceSpec


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

    request_payload = asdict(request)
    spec_payload = asdict(spec)

    assert request_payload["request_id"] == "req_001"
    assert spec_payload["acceptance_items"][0]["id"] == "AC-001"
