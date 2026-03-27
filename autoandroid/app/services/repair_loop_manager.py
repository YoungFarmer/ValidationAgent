class RepairLoopManager:
    def __init__(self, stop_conditions):
        self._stop_conditions = stop_conditions

    def next_action(self, loop_index: int, judgement_status: str, failure_type: str) -> str:
        if judgement_status == "passed":
            return "verified"
        if self._stop_conditions.should_stop(loop_index, judgement_status, failure_type):
            return "blocked"
        return "repair_requested"

    def run(self, max_loops: int, run_one_loop):
        for loop_index in range(1, max_loops + 1):
            result = run_one_loop(loop_index)
            action = self.next_action(
                loop_index=loop_index,
                judgement_status=result["judgement_status"],
                failure_type=result["failure_type"],
            )
            if action == "verified":
                return {"final_status": "verified", "completed_loops": loop_index}
            if action == "blocked":
                return {"final_status": "blocked", "completed_loops": loop_index}
        return {"final_status": "blocked", "completed_loops": max_loops}

    def run_loop(self, request, run_validation, repair_adapter, build_adapter):
        max_loops = request.constraints.get("max_loops", 1)
        source_type = request.build.get("source_type", "apk")

        for loop_index in range(1, max_loops + 1):
            result = run_validation(loop_index)
            if result["judgement_status"] == "passed":
                return {"final_status": "verified", "completed_loops": loop_index}

            if result["failure_type"] == "environment_failure":
                return {"final_status": "blocked", "completed_loops": loop_index, "reason": "environment_failure"}

            if source_type != "gradle_project":
                return {"final_status": "blocked", "completed_loops": loop_index, "reason": "immutable_artifact"}

            if loop_index >= max_loops:
                return {"final_status": "blocked", "completed_loops": loop_index, "reason": "max_loops_reached"}

            handoff = repair_adapter.send_repair_prompt(
                prompt=result["repair_prompt"],
                issues=result["issues"],
                request_id=request.request_id,
                additional_writable_dirs=[request.build.get("project_dir", "")],
            )
            if handoff.get("status") not in {"submitted", "queued"}:
                return {
                    "final_status": "blocked",
                    "completed_loops": loop_index,
                    "reason": "repair_handoff_failed",
                }

            rebuild = build_adapter.rebuild(request)
            if rebuild.get("status") != "rebuilt":
                return {
                    "final_status": "blocked",
                    "completed_loops": loop_index,
                    "reason": "rebuild_failed",
                }

        return {"final_status": "blocked", "completed_loops": max_loops, "reason": "max_loops_reached"}
