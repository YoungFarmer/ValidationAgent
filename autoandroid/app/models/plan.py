from dataclasses import dataclass
from typing import Any


@dataclass
class TestCase:
    case_id: str
    acceptance_item_id: str
    tooling: dict[str, Any]
    environment: dict[str, Any]
    assertions: list[str]
    artifacts: list[str]


@dataclass
class TestPlan:
    plan_id: str
    spec_id: str
    cases: list[TestCase]
