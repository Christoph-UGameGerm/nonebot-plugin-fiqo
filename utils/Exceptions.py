class UnsupportedOperatorError(Exception):
    def __init__(self, operator: str) -> None:
        super().__init__(f"Unsupported operator: {operator}")

class EvaluationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Evaluation error: {message}")
