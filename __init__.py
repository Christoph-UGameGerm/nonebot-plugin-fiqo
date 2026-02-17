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
    Option,
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

# ----------------------- Responders ------------------

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

fiqo_space = on_alconna(
    Alconna(
        "space",
        Args["params", StrMulti],
        Option("-w|--weight", Args["max_weight", int]),
        Option("-v|--volume", Args["max_volume", int]),
        meta=CommandMeta(
            description="计算材料总体积/重量信息",
            usage="/space <材料数量> <材料代码>...",
            example="/space 10 RAT 5 DW"
        )
    )
)
"""
space 命令
计算材料总体积/重量信息
支持多对材料数量和代码输入
"""

fiqo_fit = on_alconna(
    Alconna(
        "fit",
        Args["params", StrMulti],
        Option("-w|--weight", Args["target_weight", int]),
        Option("-v|--volume", Args["target_volume", int]),
        meta=CommandMeta(
            description="计算材料容纳量",
            usage="/fit <材料数量> <材料代码>...",
            example="/fit 10 RAT 5 DW"
        )
    )
)
"""
fit 命令
计算特定容积/重量限制下最大可携带的材料数量
支持输入多材料及其数量以限制材料比例
"""

# ------------------- Handlers ------------------

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
    await handler_helper.generic_batch_query_info_response(
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
    await handler_helper.generic_batch_query_info_response(
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

@fiqo_space.handle()
async def handle_fiqo_space(params: Match[str]) -> None:
    logger.debug("space command received.")
    if params.available:
        param_map = await handler_helper.format_param_kv_dict(params.result)
        fiqo_space.set_path_arg("params", param_map)

@fiqo_space.got_path("params", prompt="请输入材料代码和数量，格式如：10 RAT 5 DW")
async def handle_fiqo_space_calculation(
    event: SUPPORTED_MSG_EVENTS,
    bot: SUPPORTED_BOTS,
    params: dict[str, int],
    max_weight: Match[int],
    max_volume: Match[int]
) -> None:
    logger.debug(f"Received parameters for space calculation: {params}")
    helper = MessageFormatHelper()
    helper.add_head("体积重量计算结果：")

    # Define query function for all materials involved in the calculation
    query_func = partial(
        handler_helper.query_single_material,
        categories=None  # No need for categories in space calculation
    )
    # Run queries through generic handler
    results = await handler_helper.generic_batch_query_error_response_only(
        items=list(params.keys()),
        query_func=query_func,
        item_type_localized="材料",
        helper=helper
    )

    weight_sum = 0.0
    volume_sum = 0.0
    for r in results:
        if r.error_type is None and isinstance(r.info, model.MaterialInfo):
            quantity = params[r.id]
            weight_sum += r.info.weight * quantity
            volume_sum += r.info.volume * quantity

    core_message_list = [
        f"总重量: {round(weight_sum, 2)} t/吨",
        f"总体积: {round(volume_sum, 2)} m³/立方米"
    ]

    if max_weight.available:
        remaining_weight = max_weight.result - weight_sum
        core_message_list.append(f"剩余重量: {round(remaining_weight, 2)} t/吨")
    if max_volume.available:
        remaining_volume = max_volume.result - volume_sum
        core_message_list.append(f"剩余体积: {round(remaining_volume, 2)} m³/立方米")

    helper.add_core("\n".join(core_message_list))

    # Construct the final response message
    response = helper.construct_formal_response()
    logger.info(f"Final response for space command: {response}")

    # Decide sending method based on response length and content, and send the response
    if not response.only(Text) or\
        len(response.extract_plain_text()) > plugin_config.longest_single_response:
        await try_send_grouped_forward_msg(event, bot, response)
    else:
        await fiqo_space.send(response)
    await fiqo_space.finish()

@fiqo_fit.handle()
async def handle_fiqo_fit(params: Match[str]) -> None:
    logger.debug("fit command received.")
    if params.available:
        param_map = await handler_helper.format_param_kv_dict(params.result)
        fiqo_fit.set_path_arg("params", param_map)

@fiqo_fit.got_path("params", prompt="请输入材料代码和数量，格式如：10 RAT 5 DW")
async def handle_fiqo_fit_calculation(
    event: SUPPORTED_MSG_EVENTS,
    bot: SUPPORTED_BOTS,
    params: dict[str, int],
    target_weight: Match[int],
    target_volume: Match[int]
) -> None:
    logger.debug(f"Received parameters for fit calculation: {params}")
    helper = MessageFormatHelper()
    helper.add_head("材料最大容纳量计算结果：")

    # Define query function for all materials involved in the calculation
    query_func = partial(
        handler_helper.query_single_material,
        categories=None  # No need for categories in fit calculation
    )
    # Run queries through generic handler
    results = await handler_helper.generic_batch_query_error_response_only(
        items=list(params.keys()),
        query_func=query_func,
        item_type_localized="材料",
        helper=helper
    )

    # Prompt user the entered ratio of materials
    material_ratios = [f"{params[r.id]} {r.id}" for r in results\
                       if r.id in params and r.error_type is None]
    helper.add_head("材料比例: \n" + " : ".join(material_ratios))

    weight_sum = 0.0
    volume_sum = 0.0
    for r in results:
        if r.error_type is None and isinstance(r.info, model.MaterialInfo):
            quantity = params[r.id]
            weight_sum += r.info.weight * quantity
            volume_sum += r.info.volume * quantity
    weight_capacity = target_weight.result / weight_sum\
        if weight_sum > 0 else float("inf")
    volume_capacity = target_volume.result / volume_sum\
        if volume_sum > 0 else float("inf")

    max_fit_portion = int(min(weight_capacity, volume_capacity))
    fit_message_list = [
        f"最大携带份数: {max_fit_portion}",
    ]

    helper.add_core("\n".join(fit_message_list))

    if weight_capacity < volume_capacity:
        helper.add_core("受重量限制")
    elif volume_capacity < weight_capacity:
        helper.add_core("受体积限制")
    else:
        helper.add_core("同时受重量和体积限制")


    # Construct the final response message
    response = helper.construct_formal_response()
    logger.info(f"Final response for fit command: {response}")
    # Decide sending method based on response length and content, and send the response
    if not response.only(Text) or\
        len(response.extract_plain_text()) > plugin_config.longest_single_response:
        await try_send_grouped_forward_msg(event, bot, response)
    else:
        await fiqo_fit.send(response)
    await fiqo_fit.finish()
