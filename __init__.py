from nonebot import require

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")

from functools import partial

from arclet.alconna import Alconna, Args, StrMulti
from nonebot import get_plugin_config, logger
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import (
    CommandMeta,
    Match,
    Text,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_alconna import load_builtin_plugins as load_alconna_builtin_plugins

from . import exception, handler_helper, model, reply
from .ast_eval import safe_eval_four_ops
from .config import Config
from .fio_client import fio_service
from .msg_helper import (
    SUPPORTED_BOTS,
    SUPPORTED_MSG_EVENTS,
    MessageFormatHelper,
    try_send_grouped_forward_msg,
)

__plugin_meta__ = PluginMetadata(
    name="nonebot_plugin_FIQO",
    description="集成了 FIO 相关功能的 NoneBot 2 插件",
    usage="",
    type="application",
    config=Config,
)

plugin_config = get_plugin_config(Config).fiqo

load_alconna_builtin_plugins("help")

# Rules

# Permissions
global_permission = SUPERUSER

# Responders
fiqo_lorem = on_alconna(
    Alconna(
        "lorem",
        meta=CommandMeta(
            description="生成随机的占位文字",
        )
    ),
    permission=global_permission
)
"""
Lorem 命令
生成随机的占位文字
基本仅用于测试目的
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
    ),
    permission=global_permission
)
"""
math 命令
计算数学表达式的值
仅支持加减乘除四则运算
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
    ),
    permission=global_permission
)
"""
mat 命令
使用 FIO API 获取材料信息
支持多个材料名称查询
"""

fiqo_bui = on_alconna(
    Alconna(
        "bui",
        Args[
            "tickers", StrMulti
        ],
        meta=CommandMeta(
            description="获取建筑信息",
            usage="/bui <建筑代码>",
            example="/bui FRM"
        )
    ),
    permission=global_permission
)
"""
bui 命令
使用 FIO API 获取建筑信息
支持多个建筑名称查询
"""

@fiqo_lorem.handle()
async def handle_fiqo_lorem(bot: SUPPORTED_BOTS, event: SUPPORTED_MSG_EVENTS) -> None:
    logger.debug("lorem command received.")
    response = UniMessage.text(reply.LOREM)
    await try_send_grouped_forward_msg(event, bot, response)
    await fiqo_lorem.finish()


@fiqo_math.handle()
async def handle_fiqo_math(expression: Match[str]) -> None:
    logger.info("math command received.")
    if expression.available:
        expression_without_spaces = "".join(expression.result.split())
        fiqo_math.set_path_arg("expression", expression_without_spaces)

@fiqo_math.got_path("expression", prompt="请输入要计算的数学表达式！")
async def handle_fiqo_math_calculation(expression: str) -> None:
    logger.info(f"Received math expression to evaluate: {expression}")
    try:
        result = safe_eval_four_ops(expression)
        logger.info(f"Calculated result: {result}")
        await fiqo_math.finish(UniMessage.text(f"计算结果为：{result}"))
    except exception.UnsupportedOperatorError as e:
        logger.error(f"Unsupported operator error: {e}")
        await fiqo_math.finish(UniMessage.text(f"不支持的运算符：{e}"))
    except exception.EvaluationError as e:
        logger.error(f"Evaluation error: {e}")
        await fiqo_math.finish(UniMessage.text(f"计算错误，请检查表达式：{e}"))


@fiqo_mat.handle()
async def handle_fiqo_mat(tickers: Match[str]) -> None:
    logger.debug("mat command received.")
    if tickers.available:
        tickers_list = [t.upper() for t in tickers.result.split()]
        fiqo_mat.set_path_arg("tickers", tickers_list)

@fiqo_mat.got_path("tickers", prompt="请输入要查询的材料代码")
async def handle_fiqo_mat_query(
    event: SUPPORTED_MSG_EVENTS,
    bot: SUPPORTED_BOTS,
    tickers: list[str]
) -> None:
    logger.debug(f"Received query request for material tickers: {tickers}")
    helper = MessageFormatHelper()
    helper.add_head("材料信息：")

    # Query material categories as public information
    fio_categories: model.FIOCategoriesResponse | None = None
    try:
        fio_categories = await fio_service.get_material_categories()
    except exception.CategoryNotFoundError as e:
        logger.error(f"Material category not found error: {e}")
    except exception.BadConnectionError as e:
        logger.error(f"Bad connection error while fetching material categories: {e}")
    else:
        logger.debug(f"Received material categories: {fio_categories}")

    # Define query function for a single material
    query_func = partial(
        handler_helper.query_single_material,
        categories=fio_categories
    )
    # Run queries through generic handler
    await handler_helper.handle_generic_query_batch(
        items=tickers,
        query_func=query_func,
        helper=helper,
        item_type_localized="材料"
    )

    # Construct the final response message
    response = helper.construct_formal_response()
    logger.info(f"Final response for mat command: {response}")

    # Decide sending method based on response length and content, and send the response
    if not response.only(Text) or\
        len(response.extract_plain_text()) > plugin_config.longest_single_response:
        await try_send_grouped_forward_msg(event, bot, response)
    else:
        await fiqo_mat.send(response)
    await fiqo_mat.finish()


@fiqo_bui.handle()
async def handle_fiqo_bui(tickers: Match[str]) -> None:
    logger.debug("bui command received.")
    if tickers.available:
        tickers_list = [t.upper() for t in tickers.result.split()]
        fiqo_bui.set_path_arg("tickers", tickers_list)

@fiqo_bui.got_path("tickers", prompt="请输入要查询的建筑代码")
async def handle_fiqo_bui_query(
    event: SUPPORTED_MSG_EVENTS,
    bot: SUPPORTED_BOTS,
    tickers: list[str]
) -> None:
    logger.debug(f"Received query request for building tickers: {tickers}")
    helper = MessageFormatHelper()
    helper.add_head("建筑信息：")

    # Define query function for a single building
    query_func = handler_helper.query_single_building
    # Run queries through generic handler
    await handler_helper.handle_generic_query_batch(
        items=tickers,
        query_func=query_func,
        helper=helper,
        item_type_localized="建筑"
    )

    # Construct the final response message
    response = helper.construct_formal_response()
    logger.info(f"Final response for bui command: {response}")

    # Decide sending method based on response length and content, and send the response
    if not response.only(Text) or\
        len(response.extract_plain_text()) > plugin_config.longest_single_response:
        await try_send_grouped_forward_msg(event, bot, response)
    else:
        await fiqo_bui.send(response)
    await fiqo_bui.finish()
