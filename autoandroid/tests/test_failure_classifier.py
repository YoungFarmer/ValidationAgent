from autoandroid.app.models.run import CaseResult
from autoandroid.app.rules.failure_classifier import FailureClassifier


def test_failure_classifier_marks_maestro_permission_error_as_environment_failure():
    case_result = CaseResult(
        case_id="CASE-001",
        status="failed",
        steps=[{"name": "run maestro flow", "status": "failed"}],
        artifacts={
            "stderr": "java.nio.file.FileSystemException: /Users/liuji/.maestro/deps/applesimutils: Operation not permitted"
        },
    )

    assert FailureClassifier().classify(case_result) == "environment_failure"


def test_failure_classifier_marks_generic_failed_case_as_product_bug():
    case_result = CaseResult(
        case_id="CASE-002",
        status="failed",
        steps=[{"name": "assert visible", "status": "failed"}],
        artifacts={"stderr": ""},
    )

    assert FailureClassifier().classify(case_result) == "product_bug"
