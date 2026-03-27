from autoandroid.app.services.prompt_builder import PromptBuilder


def test_prompt_builder_includes_issue_context():
    builder = PromptBuilder()
    issue = builder.build_issue_report("AC-001", "Coupon entry missing")
    prompt = builder.build_repair_prompt(issue)

    assert "AC-001" in prompt
    assert "Coupon entry missing" in prompt


def test_prompt_builder_includes_evidence_paths_in_repair_prompt():
    builder = PromptBuilder()
    issue = builder.build_issue_report(
        "AC-001",
        "Coupon entry missing",
        evidence={
            "flow_path": "autoandroid/flows/generated/ac-001.yaml",
            "output_dir": "autoandroid/flows/artifacts/case-001",
            "stderr": "assert visible failed",
        },
    )
    prompt = builder.build_repair_prompt(issue)

    assert "autoandroid/flows/generated/ac-001.yaml" in prompt
    assert "autoandroid/flows/artifacts/case-001" in prompt
