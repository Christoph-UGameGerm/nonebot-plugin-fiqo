class UnsupportedOperatorError(Exception):
    def __init__(self, operator: str) -> None:
        super().__init__(f"Unsupported operator: {operator}")

class EvaluationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Evaluation error: {message}")

class WrongMaterialTickerError(Exception):
    def __init__(self, tickers: list[str]) -> None:
        super().__init__(f"Wrong material ticker: {tickers}")

class BadConnectionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Bad connection error: {message}")
