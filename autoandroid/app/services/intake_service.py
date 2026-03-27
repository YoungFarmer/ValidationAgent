import json
from pathlib import Path

from autoandroid.app.models.request import ValidationRequest


class IntakeService:
    def load_request(self, path: str) -> ValidationRequest:
        payload = json.loads(Path(path).read_text())
        return ValidationRequest(**payload)
