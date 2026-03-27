from autoandroid.app.rules.stop_conditions import StopConditions
from autoandroid.app.services.repair_loop_manager import RepairLoopManager


def test_repair_loop_manager_retries_until_success():
    manager = RepairLoopManager(stop_conditions=StopConditions(max_loops=3))
    calls = []

    responses = [
        {"judgement_status": "failed", "failure_type": "product_bug"},
        {"judgement_status": "passed", "failure_type": "unknown"},
    ]

    def run_one_loop(loop_index: int):
        calls.append(loop_index)
        return responses[loop_index - 1]

    result = manager.run(max_loops=3, run_one_loop=run_one_loop)

    assert calls == [1, 2]
    assert result["final_status"] == "verified"
    assert result["completed_loops"] == 2


def test_repair_loop_manager_stops_on_environment_failure():
    manager = RepairLoopManager(stop_conditions=StopConditions(max_loops=3))

    def run_one_loop(loop_index: int):
        return {"judgement_status": "failed", "failure_type": "environment_failure"}

    result = manager.run(max_loops=3, run_one_loop=run_one_loop)

    assert result["final_status"] == "blocked"
    assert result["completed_loops"] == 1
