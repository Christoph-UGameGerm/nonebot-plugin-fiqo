from arclet.alconna import StrMulti
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, on_alconna

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.services import math_service
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.utils import (
    decorators,
    execute_batch,
    global_formatter,
)

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_math = on_alconna(
    Alconna(
        "math",
        Args["expression#表达式", StrMulti],
        meta=CommandMeta(
            description="计算数学表达式的值",
            usage="/math <expression>",
            example="/math 2 + 2 * (3 - 1)",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_math.handle()
@decorators.handle_log_and_err()
async def _(expression: str) -> None:
    result = await execute_batch([expression], math_service.safe_eval)
    response = global_formatter.format_service_result(result, "计算结果：")
    await fiqo_math.finish(response)
