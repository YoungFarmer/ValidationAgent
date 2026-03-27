from autoandroid.app.models.plan import TestCase, TestPlan
from autoandroid.app.models.spec import AcceptanceSpec


class TestPlanner:
    def build(self, spec: AcceptanceSpec) -> TestPlan:
        cases = []
        for index, item in enumerate(spec.acceptance_items, start=1):
            cases.append(
                TestCase(
                    case_id=f"CASE-{index:03d}",
                    acceptance_item_id=item.id,
                    tooling={
                        "maestro_flow": f"autoandroid/flows/generated/{item.id.lower()}.yaml",
                        "adb_commands": ["adb logcat -c"],
                    },
                    environment={"device_type": "emulator"},
                    assertions=item.expected,
                    artifacts=item.evidence,
                )
            )
        return TestPlan(plan_id=f"plan_{spec.spec_id}", spec_id=spec.spec_id, cases=cases)
