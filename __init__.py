from arclet.alconna import Alconna, Args, MultiVar, StrMulti
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import CommandMeta, Match, on_alconna

from .config import Config
from .resources import Models, Replys
from .utils import Exceptions
from .utils.ast_eval import safe_eval_four_ops

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_FIQO",
    description="集成了 FIO 相关功能的 NoneBot 2 插件",
    usage="",
    type="application",
    config=Config,
)

plugin_config = get_plugin_config(Config)

# Responders
"""
Lorem 命令
生成随机的占位文字
基本仅用于测试目的
"""
fiqo_lorem = on_alconna(
    Alconna(
        "lorem",
        meta=CommandMeta(
            description="生成随机的占位文字",
        )
    )
)

@fiqo_lorem.handle()
async def handle_fiqo_lorem() -> None:
    await fiqo_lorem.finish(Replys.LOREM)

"""
math 命令
计算数学表达式的值
仅支持加减乘除四则运算
"""
fiqo_math = on_alconna(
    Alconna(
        "math",
        Args[
            "expression", StrMulti
        ],
        meta=CommandMeta(
            description="计算数学表达式的值",
            usage="/math <expression>",
            example="/math 2 + 2 * (3 - 1)",
        )
    )
)

@fiqo_math.handle()
async def handle_fiqo_math(expression: Match[str]) -> None:
    if expression.available:
        expression_without_spaces = "".join(expression.result.split())
        fiqo_math.set_path_arg("expression", expression_without_spaces)

@fiqo_math.got_path("expression", prompt="请输入要计算的数学表达式！")
async def handle_fiqo_math_calculation(expression: str) -> None:
    try:
        result = safe_eval_four_ops(expression)
        await fiqo_math.finish(f"计算结果为：{result}")
    except Exceptions.UnsupportedOperatorError as e:
        await fiqo_math.finish(f"不支持的运算符：{e}")
    except Exceptions.EvaluationError as e:
        await fiqo_math.finish(f"计算错误，请检查表达式：{e}")
