class UnsupportedOperatorError(Exception):
    def __init__(self, operator: str) -> None:
        super().__init__(f"不支持的运算符: {operator}")

class EvaluationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"计算错误: {message}")

class WrongMaterialTickerError(Exception):
    def __init__(self, ticker: str) -> None:
        super().__init__(f"错误的材料代码: {ticker}")

class WrongBuildingTickerError(Exception):
    def __init__(self, ticker: str) -> None:
        super().__init__(f"错误的建筑代码: {ticker}")

class CategoryNotFoundError(Exception):
    def __init__(self, category: str="") -> None:
        super().__init__(f"获取FIO物品类别{category}失败")

class BadConnectionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"网络错误: {message}")

class I18nFetchError(Exception):
    def __init__(self, unit: str, message: str) -> None:
        super().__init__(f" {unit} 的 I18n 信息获取错误: '{message}'")

class I18nKeyError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Weblate 条目键值错误: {key}")
