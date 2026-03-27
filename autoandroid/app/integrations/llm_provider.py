from typing import Protocol


class LlmProvider(Protocol):
    def generate_structured_json(self, template_name: str, context: dict) -> dict:
        ...
