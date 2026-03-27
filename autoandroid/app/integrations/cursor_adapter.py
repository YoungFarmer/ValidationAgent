class CursorAdapter:
    def send_repair_prompt(self, prompt: str, issues: list[dict], request_id: str) -> dict:
        return {
            "status": "queued",
            "target": "cursor",
            "request_id": request_id,
            "issue_count": len(issues),
            "prompt_preview": prompt.splitlines()[0] if prompt else "",
        }
