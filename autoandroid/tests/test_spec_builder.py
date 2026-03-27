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
                    "evidence": ["screenshot"],
                }
            ],
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


def test_spec_builder_supports_structured_acceptance_items_without_llm():
    request = ValidationRequest(
        request_id="req_002",
        feature_name="sunflower launch",
        goal="verify launch smoke flow",
        requirement_sources=[
            {
                "type": "acceptance_item",
                "title": "Launch app and show empty garden state",
                "priority": "high",
                "steps": ["launch app"],
                "expected": ["My garden", "Your garden is empty", "Add plant"],
                "evidence": ["screenshot"],
            }
        ],
        build={"source_type": "apk", "ref": "app-debug.apk"},
        environment={"platform": "android", "mode": "connected_device"},
        credentials={"profiles": []},
        constraints={"max_loops": 1},
    )

    builder = SpecBuilder(llm_provider=None)
    spec = builder.build(request)

    assert spec.feature_name == "sunflower launch"
    assert spec.acceptance_items[0].expected == ["My garden", "Your garden is empty", "Add plant"]
