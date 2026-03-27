class FailureClassifier:
    def classify(self, case_result) -> str:
        stderr = case_result.artifacts.get("stderr", "")
        if "Operation not permitted" in stderr or "FileSystemException" in stderr:
            return "environment_failure"
        if case_result.status == "failed":
            return "product_bug"
        return "unknown"
