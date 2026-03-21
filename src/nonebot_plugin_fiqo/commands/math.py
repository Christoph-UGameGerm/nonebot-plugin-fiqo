from arclet.alconna import StrMulti
from nonebot_plugin_alconna import Args, Alconna, CommandMeta, on_alconna

from nonebot_plugin_fiqo.utils import (
    decorators,
    execute_batch,
    global_formatter,
)
from nonebot_plugin_fiqo.services import math_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_math = on_alconna(
    Alconna(
        "math",
        Args["expression#表达式", StrMulti],
        meta=CommandMeta(
            description="[普通用户] 计算数学表达式的值",
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
