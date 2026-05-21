import ast
import math
import operator

from nonebot_plugin_fiqo.models import (
    MaterialDTO,
    FitResultDTO,
    FitRatioItemDTO,
    FitRatioResultDTO,
)
from nonebot_plugin_fiqo.exceptions import EvaluationError, UnsupportedOperatorError

operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class MathService:
    @staticmethod
    def _calculate_capacity_result(
        unit_weight: float,
        unit_volume: float,
        max_weight: float,
        max_volume: float,
    ) -> tuple[int, float, float, str]:
        if unit_weight <= 0 or unit_volume <= 0:
            raise EvaluationError("材料重量或体积异常，无法计算装载数量")
        if max_weight < 0 or max_volume < 0:
            raise EvaluationError("重量和体积上限不能为负数")

        max_by_weight = math.floor(max_weight / unit_weight)
        max_by_volume = math.floor(max_volume / unit_volume)
        max_units = min(max_by_weight, max_by_volume)
        remaining_weight = max_weight - max_units * unit_weight
        remaining_volume = max_volume - max_units * unit_volume

        if max_by_weight < max_by_volume:
            limiting_factor = "重量受限"
        elif max_by_volume < max_by_weight:
            limiting_factor = "体积受限"
        else:
            limiting_factor = "双重受限"

        return max_units, remaining_weight, remaining_volume, limiting_factor

    @staticmethod
    def safe_eval_four_ops(expr: str) -> float:
        """
        Safely evaluate a mathematical expression containing only
        addition, subtraction, multiplication, and division.

        Args:
            expr (str): The mathematical expression to evaluate.
        Returns:
            float: The result of the evaluated expression.
        Raises:
            ValueError: If the expression contains unsupported operations.
        """

        def _eval(node: ast.AST) -> float:
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value

            elif isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                op_type = type(node.op)
                if op_type in operators:
                    return operators[op_type](left, right)

            elif isinstance(node, ast.UnaryOp):
                operand = _eval(node.operand)
                op_type = type(node.op)
                if op_type in operators:
                    return operators[op_type](operand)

            bad_code = ast.unparse(node)
            raise UnsupportedOperatorError(bad_code)

        try:
            tree = ast.parse(expr, mode="eval")
            return _eval(tree.body)
        except UnsupportedOperatorError:
            raise
        except Exception as e:
            raise EvaluationError(str(e)) from e

    @staticmethod
    async def safe_eval(expr: str) -> str:
        val = MathService.safe_eval_four_ops(expr)
        return str(val)

    @staticmethod
    def calculate_fit(
        material: MaterialDTO,
        max_weight: float,
        max_volume: float,
        preset_key: str | None = None,
        preset_name: str | None = None,
        preset_weight: float | None = None,
        preset_volume: float | None = None,
    ) -> FitResultDTO:
        max_units, remaining_weight, remaining_volume, limiting_factor = (
            MathService._calculate_capacity_result(
                material.weight,
                material.volume,
                max_weight,
                max_volume,
            )
        )

        return FitResultDTO(
            ticker=material.ticker,
            material_name=material.name,
            max_units=max_units,
            remaining_weight=remaining_weight,
            remaining_volume=remaining_volume,
            limiting_factor=limiting_factor,
            unit_weight=material.weight,
            unit_volume=material.volume,
            preset_key=preset_key,
            preset_name=preset_name,
            preset_weight=preset_weight,
            preset_volume=preset_volume,
        )

    @staticmethod
    def calculate_fitratio(
        items: list[FitRatioItemDTO],
        max_weight: float,
        max_volume: float,
        preset_key: str | None = None,
        preset_name: str | None = None,
        preset_weight: float | None = None,
        preset_volume: float | None = None,
    ) -> FitRatioResultDTO:
        if not items:
            raise EvaluationError("请至少提供一种材料")

        group_weight = sum(item.total_weight for item in items)
        group_volume = sum(item.total_volume for item in items)
        max_groups, remaining_weight, remaining_volume, limiting_factor = (
            MathService._calculate_capacity_result(
                group_weight,
                group_volume,
                max_weight,
                max_volume,
            )
        )

        return FitRatioResultDTO(
            max_groups=max_groups,
            remaining_weight=remaining_weight,
            remaining_volume=remaining_volume,
            limiting_factor=limiting_factor,
            group_weight=group_weight,
            group_volume=group_volume,
            items=items,
            preset_key=preset_key,
            preset_name=preset_name,
            preset_weight=preset_weight,
            preset_volume=preset_volume,
        )


math_service = MathService()
