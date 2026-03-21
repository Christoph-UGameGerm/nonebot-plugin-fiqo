class FIQOBaseError(Exception):
    pass


# =============================================
# Calculation and Resolve Errors
# =============================================


class EvaluationError(FIQOBaseError):
    def __init__(self, message: str) -> None:
        self.err_message = message
        super().__init__(f"计算错误: {message}")


class UnsupportedOperatorError(EvaluationError):
    def __init__(self, operator: str) -> None:
        self.operator = operator
        super().__init__(f"不支持的运算符: {operator}")


# =============================================
# Resource and Ticker Fetching Errors
# =============================================


class ResourceNotFoundError(FIQOBaseError):
    def __init__(self, resource_type: str, identifier: str) -> None:
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"错误的{resource_type}: {identifier}")


class WrongMaterialTickerError(ResourceNotFoundError):
    def __init__(self, ticker: str) -> None:
        super().__init__("材料代码", ticker)


class WrongBuildingTickerError(ResourceNotFoundError):
    def __init__(self, ticker: str) -> None:
        super().__init__("建筑代码", ticker)


class WrongCXTickerError(ResourceNotFoundError):
    def __init__(self, ticker: str) -> None:
        super().__init__("CX代码", ticker)


class WrongRecipeTickerError(ResourceNotFoundError):
    def __init__(self, ticker: str) -> None:
        super().__init__("配方代码", ticker)

class WrongUsernameOrCompanyTickerError(ResourceNotFoundError):
    def __init__(self, ticker: str) -> None:
        super().__init__("用户名、公司名或代码", ticker)


class CategoryNotFoundError(ResourceNotFoundError):
    def __init__(self, category: str = "") -> None:
        super().__init__("FIO物品类别", category)


# =============================================
# Network and Communication Errors
# =============================================


class BadConnectionError(FIQOBaseError):
    def __init__(self, message: str) -> None:
        self.err_message = message
        super().__init__(f"网络错误: {message}")


# =============================================
# I18n Errors
# =============================================


class I18nNotFoundError(ResourceNotFoundError):
    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__("Weblate查询", query)


class I18nFetchError(FIQOBaseError):
    def __init__(self, message: str) -> None:
        self.err_message = message
        super().__init__(f"I18n 信息获取错误: '{message}'")
