from autoandroid.app.models.run import JudgementItemResult, JudgementResult


class JudgementService:
    def judge(self, spec, run):
        item_results = []
        failed = 0
        for item, case in zip(spec.acceptance_items, run.case_results):
            status = "passed" if case.status == "passed" else "failed"
            if status == "failed":
                failed += 1
            item_results.append(
                JudgementItemResult(
                    acceptance_item_id=item.id,
                    status=status,
                    reason="execution failed" if status == "failed" else "all assertions satisfied",
                    linked_case_ids=[case.case_id],
                    confidence=0.95 if status == "passed" else 0.9,
                )
            )

        return JudgementResult(
            judgement_id=f"judge_{run.run_id}",
            run_id=run.run_id,
            summary={
                "total_acceptance_items": len(spec.acceptance_items),
                "passed": len(spec.acceptance_items) - failed,
                "failed": failed,
                "uncertain": 0,
                "final_status": "failed" if failed else "passed",
            },
            item_results=item_results,
        )
