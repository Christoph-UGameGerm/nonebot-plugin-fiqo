from arclet.alconna import Arparma
from nonebot_plugin_alconna import (
    Args,
    Option,
    Alconna,
    MultiVar,
    CommandMeta,
    on_alconna,
)

from nonebot_plugin_fiqo.utils import global_formatter
from nonebot_plugin_fiqo.services import fit_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_fitratio = on_alconna(
    Alconna(
        "fitratio",
        Args["tokens#材料组合与载荷参数", MultiVar(str)],
        Option("-s|--ship", Args["ship_preset#运力预设", str]),
        meta=CommandMeta(
            description="[普通用户] 计算给定材料组合在载荷下最多可装载多少组",
            usage=(
                "/fitratio <组合> <重量>t <体积>m，/fitratio <组合> <preset>，"
                "或 /fitratio <组合> [-s|--ship] <preset>"
            ),
            example=(
                "/fitratio 2AEF 3MCG HSE 3000t 1000m，"
                "/fitratio 2 AEF 3 MCG HSE LCB，"
                "/fitratio 2AEF 3MCG HSE -s LCB"
            ),
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_fitratio.handle()
async def _(param: Arparma) -> None:
    tokens = param.query[list[str]]("tokens") or []
    ship_preset = param.query[str]("ship_preset")

    result = await fit_service.get_fitratio_result(
        tokens=tokens,
        ship_preset=ship_preset,
    )
    response = global_formatter.format_service_result(result, "装载配比计算：\n")
    await fiqo_fitratio.finish(response)
