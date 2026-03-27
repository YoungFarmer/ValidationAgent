class StopConditions:
    def __init__(self, max_loops: int):
        self._max_loops = max_loops

    def should_stop(self, loop_index: int, judgement_status: str, failure_type: str) -> bool:
        if judgement_status == "passed":
            return True
        if failure_type == "environment_failure":
            return True
        return loop_index >= self._max_loops
