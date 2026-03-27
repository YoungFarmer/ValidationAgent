from autoandroid.app.models.issue import IssueReport


class PromptBuilder:
    def build_issue_report(self, acceptance_item_id: str, title: str, evidence=None) -> IssueReport:
        return IssueReport(
            issue_id="ISSUE-001",
            severity="high",
            acceptance_item_id=acceptance_item_id,
            title=title,
            reproduction_steps=["reproduce with validation flow"],
            expected_result="acceptance item passes",
            actual_result="acceptance item failed",
            evidence=evidence or {},
            suspected_causes=["implementation incomplete"],
            repair_hint="inspect the feature logic and rerun validation",
        )

    def build_repair_prompt(self, issue: IssueReport) -> str:
        prompt = (
            f"Fix acceptance item {issue.acceptance_item_id}: {issue.title}\n"
            f"Expected: {issue.expected_result}\n"
            f"Actual: {issue.actual_result}\n"
            f"Hint: {issue.repair_hint}\n"
        )
        if issue.evidence:
            prompt += "Evidence:\n"
            for key, value in issue.evidence.items():
                prompt += f"- {key}: {value}\n"
        return prompt
