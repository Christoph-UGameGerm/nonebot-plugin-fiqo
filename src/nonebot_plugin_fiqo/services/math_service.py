import ast
import operator

from nonebot_plugin_fiqo.exceptions import (
    EvaluationError,
    UnsupportedOperatorError,
)

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


math_service = MathService()
