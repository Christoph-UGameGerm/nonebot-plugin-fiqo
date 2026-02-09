class UnsupportedOperatorError(Exception):
    def __init__(self, operator: str) -> None:
        super().__init__(f"Unsupported operator: {operator}")

class EvaluationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Evaluation error: {message}")

class WrongMaterialTickerError(Exception):
    def __init__(self, tickers: list[str]) -> None:
        super().__init__(f"Wrong material ticker: {tickers}")

class CategoryNotFoundError(Exception):
    def __init__(self, category_id: str) -> None:
        super().__init__(f"Category not found for ID: {category_id}")

class BadConnectionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Bad connection error: {message}")

class I18nFetchError(Exception):
    def __init__(self, unit: str, message: str) -> None:
        super().__init__(f"I18n fetch error for {unit}: '{message}'")

class I18nKeyError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Weblate key error for: {key}")
