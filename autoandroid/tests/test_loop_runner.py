from autoandroid.app.services.repair_loop_manager import RepairLoopManager


class StubRepairAdapter:
    def __init__(self):
        self.calls = []

    def send_repair_prompt(
        self,
        prompt: str,
        issues: list[dict],
        request_id: str,
        additional_writable_dirs: list[str] | None = None,
    ) -> dict:
        self.calls.append((prompt, issues, request_id, additional_writable_dirs))
        return {"status": "submitted", "request_id": request_id}


class StubBuildAdapter:
    def __init__(self):
        self.calls = []

    def rebuild(self, request) -> dict:
        self.calls.append(request.request_id)
        return {"status": "rebuilt", "artifact": request.build.get("ref", "")}


def test_loop_runner_rebuilds_and_retries_for_project_requests():
    manager = RepairLoopManager(stop_conditions=None)
    repair_adapter = StubRepairAdapter()
    build_adapter = StubBuildAdapter()
    calls = []

    request = type(
        "Request",
        (),
        {
            "request_id": "req_loop",
            "constraints": {"max_loops": 3},
            "build": {"source_type": "gradle_project", "ref": "/tmp/app-debug.apk"},
        },
    )()

    def run_validation(loop_index: int):
        calls.append(loop_index)
        if loop_index == 1:
            return {
                "judgement_status": "failed",
                "failure_type": "product_bug",
                "issues": [{"acceptance_item_id": "AC-001"}],
                "repair_prompt": "Fix AC-001",
            }
        return {
            "judgement_status": "passed",
            "failure_type": "unknown",
            "issues": [],
            "repair_prompt": "",
        }

    result = manager.run_loop(
        request=request,
        run_validation=run_validation,
        repair_adapter=repair_adapter,
        build_adapter=build_adapter,
    )

    assert result["final_status"] == "verified"
    assert calls == [1, 2]
    assert repair_adapter.calls[0][2] == "req_loop"
    assert repair_adapter.calls[0][3] == [""]
    assert build_adapter.calls == ["req_loop"]


def test_loop_runner_blocks_when_request_uses_static_apk():
    manager = RepairLoopManager(stop_conditions=None)
    repair_adapter = StubRepairAdapter()
    build_adapter = StubBuildAdapter()

    request = type(
        "Request",
        (),
        {
            "request_id": "req_static",
            "constraints": {"max_loops": 3},
            "build": {"source_type": "apk", "ref": "/tmp/app-debug.apk"},
        },
    )()

    def run_validation(loop_index: int):
        return {
            "judgement_status": "failed",
            "failure_type": "product_bug",
            "issues": [{"acceptance_item_id": "AC-001"}],
            "repair_prompt": "Fix AC-001",
        }

    result = manager.run_loop(
        request=request,
        run_validation=run_validation,
        repair_adapter=repair_adapter,
        build_adapter=build_adapter,
    )

    assert result["final_status"] == "blocked"
    assert result["reason"] == "immutable_artifact"
    assert repair_adapter.calls == []
    assert build_adapter.calls == []


def test_loop_runner_blocks_when_codex_handoff_fails():
    manager = RepairLoopManager(stop_conditions=None)
    build_adapter = StubBuildAdapter()

    request = type(
        "Request",
        (),
        {
            "request_id": "req_handoff_fail",
            "constraints": {"max_loops": 3},
            "build": {"source_type": "gradle_project", "ref": "/tmp/app-debug.apk"},
        },
    )()

    class FailingRepairAdapter:
        def send_repair_prompt(
            self,
            prompt: str,
            issues: list[dict],
            request_id: str,
            additional_writable_dirs: list[str] | None = None,
        ) -> dict:
            return {"status": "failed", "request_id": request_id}

    def run_validation(loop_index: int):
        return {
            "judgement_status": "failed",
            "failure_type": "product_bug",
            "issues": [{"acceptance_item_id": "AC-001"}],
            "repair_prompt": "Fix AC-001",
        }

    result = manager.run_loop(
        request=request,
        run_validation=run_validation,
        repair_adapter=FailingRepairAdapter(),
        build_adapter=build_adapter,
    )

    assert result["final_status"] == "blocked"
    assert result["reason"] == "repair_handoff_failed"
    assert build_adapter.calls == []


def test_loop_runner_blocks_when_rebuild_fails():
    manager = RepairLoopManager(stop_conditions=None)
    repair_adapter = StubRepairAdapter()

    request = type(
        "Request",
        (),
        {
            "request_id": "req_build_fail",
            "constraints": {"max_loops": 3},
            "build": {"source_type": "gradle_project", "ref": "/tmp/app-debug.apk"},
        },
    )()

    class FailingBuildAdapter:
        def __init__(self):
            self.calls = []

        def rebuild(self, request) -> dict:
            self.calls.append(request.request_id)
            return {"status": "failed"}

    build_adapter = FailingBuildAdapter()

    def run_validation(loop_index: int):
        return {
            "judgement_status": "failed",
            "failure_type": "product_bug",
            "issues": [{"acceptance_item_id": "AC-001"}],
            "repair_prompt": "Fix AC-001",
        }

    result = manager.run_loop(
        request=request,
        run_validation=run_validation,
        repair_adapter=repair_adapter,
        build_adapter=build_adapter,
    )

    assert result["final_status"] == "blocked"
    assert result["reason"] == "rebuild_failed"
    assert build_adapter.calls == ["req_build_fail"]
