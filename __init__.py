from arclet.alconna import Alconna, Args, StrMulti
from nonebot import get_plugin_config, logger
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import CommandMeta, Match, UniMessage, on_alconna
from nonebot_plugin_alconna import load_builtin_plugins as load_alconna_builtin_plugins

from .config import Config
from .resources import Models, Replys
from .utils import Exceptions
from .utils.ast_eval import safe_eval_four_ops
from .utils.FioClient import fio_service

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_FIQO",
    description="集成了 FIO 相关功能的 NoneBot 2 插件",
    usage="",
    type="application",
    config=Config,
)

plugin_config = get_plugin_config(Config)


load_alconna_builtin_plugins("help")

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
    logger.debug("lorem command received.")
    await fiqo_lorem.finish(
        UniMessage.text(Replys.LOREM)
    )

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
    logger.debug("math command received.")
    if expression.available:
        expression_without_spaces = "".join(expression.result.split())
        fiqo_math.set_path_arg("expression", expression_without_spaces)

@fiqo_math.got_path("expression", prompt="请输入要计算的数学表达式！")
async def handle_fiqo_math_calculation(expression: str) -> None:
    logger.debug(f"Received math expression to evaluate: {expression}")
    try:
        result = safe_eval_four_ops(expression)
        logger.debug(f"Calculated result: {result}")
        await fiqo_math.finish(UniMessage.text(f"计算结果为：{result}"))
    except Exceptions.UnsupportedOperatorError as e:
        logger.debug(f"Unsupported operator error: {e}")
        await fiqo_math.finish(UniMessage.text(f"不支持的运算符：{e}"))
    except Exceptions.EvaluationError as e:
        logger.debug(f"Evaluation error: {e}")
        await fiqo_math.finish(UniMessage.text(f"计算错误，请检查表达式：{e}"))

"""
mat 命令
使用 FIO API 获取材料信息
支持多个材料名称查询
"""

fiqo_mat = on_alconna(
    Alconna(
        "mat",
        Args[
            "tickers", StrMulti
        ],
        meta=CommandMeta(
            description="获取材料信息",
            usage="/mat <材料代码>",
            example="/mat RAT"
        )
    )
)

@fiqo_mat.handle()
async def handle_fiqo_mat(tickers: Match[str]) -> None:
    logger.debug("mat command received.")
    if tickers.available:
        tickers_list = [t.upper() for t in tickers.result.split()]
        fiqo_mat.set_path_arg("tickers", tickers_list)

@fiqo_mat.got_path("tickers", prompt="请输入要查询的材料代码")
async def handle_fiqo_mat_query(tickers: list[str]) -> None:
    logger.debug(f"Received query request for material tickers: {tickers}")
    response: UniMessage = UniMessage.text("物品信息：")
    try:
        raw_material_info_list = await fio_service.get_material_info(tickers)
        logger.debug(f"Received material info response: {raw_material_info_list}")
        if not raw_material_info_list:
            await fiqo_mat.send(
                response.text("未找到对应的材料信息，请检查材料代码是否正确。")
            )
        else:
            for info in raw_material_info_list:
                response.text("\n-------------------\n")
                material = Models.MaterialInfo.model_validate(info)
                logger.debug(f"Parsed material info: {material}")
                response.text(str(material))
    except Exceptions.WrongMaterialTickerError as e:
        logger.debug(f"Wrong material ticker error: {e}")
        await fiqo_mat.send(UniMessage.text(f"错误的材料代码：{e}"))
    except Exceptions.BadConnectionError as e:
        logger.error(f"Bad connection error: {e}")
        await fiqo_mat.send(UniMessage.text(f"连接 FIO 服务时出错：{e}"))
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        await fiqo_mat.send(UniMessage.text(f"发生错误：{e}"))
        raise
    finally:
        logger.debug("Finish handling mat command.")
        await fiqo_mat.finish(response)
