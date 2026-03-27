from autoandroid.app.rules.stop_conditions import StopConditions


def test_stop_conditions_blocks_after_max_loops():
    rules = StopConditions(max_loops=3)
    should_stop = rules.should_stop(loop_index=3, judgement_status="failed", failure_type="product_bug")

    assert should_stop is True
