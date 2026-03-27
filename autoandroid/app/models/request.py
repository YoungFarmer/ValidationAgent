from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationRequest:
    request_id: str
    feature_name: str
    goal: str
    requirement_sources: list[dict[str, Any]]
    build: dict[str, Any]
    environment: dict[str, Any]
    credentials: dict[str, Any]
    constraints: dict[str, Any]
