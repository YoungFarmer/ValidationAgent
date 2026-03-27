from dataclasses import dataclass
from typing import Any


@dataclass
class IssueReport:
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
