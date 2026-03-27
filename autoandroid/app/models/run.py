from dataclasses import dataclass
from typing import Any


@dataclass
class CaseResult:
    case_id: str
    status: str
    steps: list[dict[str, Any]]
    artifacts: dict[str, Any]


@dataclass
class ExecutionRun:
    run_id: str
    request_id: str
    plan_id: str
    status: str
    device: dict[str, Any]
    started_at: str
    finished_at: str
    case_results: list[CaseResult]


@dataclass
class JudgementItemResult:
    acceptance_item_id: str
    status: str
    reason: str
    linked_case_ids: list[str]
    confidence: float


@dataclass
class JudgementResult:
    judgement_id: str
    run_id: str
    summary: dict[str, Any]
    item_results: list[JudgementItemResult]
