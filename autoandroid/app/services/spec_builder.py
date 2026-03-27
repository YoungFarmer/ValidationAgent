from autoandroid.app.models.request import ValidationRequest
from autoandroid.app.models.spec import AcceptanceItem, AcceptanceSpec


class SpecBuilder:
    def __init__(self, llm_provider):
        self._llm_provider = llm_provider

    def build(self, request: ValidationRequest) -> AcceptanceSpec:
        if self._llm_provider is None:
            return self._build_from_structured_sources(request)

        payload = self._llm_provider.generate_structured_json(
            "acceptance_spec_prompt.md",
            {
                "feature_name": request.feature_name,
                "goal": request.goal,
                "requirement_sources": request.requirement_sources,
            },
        )
        items = [AcceptanceItem(**item) for item in payload["acceptance_items"]]
        return AcceptanceSpec(
            spec_id=payload["spec_id"],
            feature_name=payload["feature_name"],
            in_scope=payload["in_scope"],
            out_of_scope=payload["out_of_scope"],
            acceptance_items=items,
        )

    def _build_from_structured_sources(self, request: ValidationRequest) -> AcceptanceSpec:
        acceptance_items = []
        for index, source in enumerate(request.requirement_sources, start=1):
            if source.get("type") != "acceptance_item":
                continue
            acceptance_items.append(
                AcceptanceItem(
                    id=f"AC-{index:03d}",
                    title=source["title"],
                    type=source.get("item_type", "ui"),
                    priority=source.get("priority", "medium"),
                    preconditions=source.get("preconditions", []),
                    steps=source.get("steps", []),
                    expected=source.get("expected", []),
                    evidence=source.get("evidence", ["screenshot"]),
                )
            )

        return AcceptanceSpec(
            spec_id=f"spec_{request.request_id}",
            feature_name=request.feature_name,
            in_scope=[item.title for item in acceptance_items],
            out_of_scope=[],
            acceptance_items=acceptance_items,
        )
