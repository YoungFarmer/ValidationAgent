from dataclasses import dataclass


@dataclass
class AcceptanceItem:
    id: str
    title: str
    type: str
    priority: str
    preconditions: list[str]
    steps: list[str]
    expected: list[str]
    evidence: list[str]


@dataclass
class AcceptanceSpec:
    spec_id: str
    feature_name: str
    in_scope: list[str]
    out_of_scope: list[str]
    acceptance_items: list[AcceptanceItem]
