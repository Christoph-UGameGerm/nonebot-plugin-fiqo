from arclet.alconna import Arparma
from nonebot_plugin_alconna import Args, Option, Alconna, CommandMeta, on_alconna

from nonebot_plugin_fiqo.utils import global_formatter
from nonebot_plugin_fiqo.services import fit_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_fit = on_alconna(
    Alconna(
        "fit",
        Args["ticker#材料代码", str]["capacity_1#载荷参数1", str, None][
            "capacity_2#载荷参数2", str, None
        ],
        Option("-s|--ship", Args["ship_preset#运力预设", str]),
        meta=CommandMeta(
            description="[普通用户] 计算给定载荷下可装载的材料数量",
            usage=(
                "/fit <ticker> <重量>t <体积>m，/fit <ticker> <preset>，"
                "或 /fit <ticker> [-s|--ship] <preset>"
            ),
            example=(
                "/fit AEF 3000t 1000m，/fit AEF 1000m 3000t，"
                "/fit AEF LCB，/fit AEF -s LCB"
            ),
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_fit.handle()
async def _(param: Arparma) -> None:
    ticker = param.query[str]("ticker")
    capacity_1 = param.query[str]("capacity_1")
    capacity_2 = param.query[str]("capacity_2")
    ship_preset = param.query[str]("ship_preset")

    result = await fit_service.get_fit_result(
        ticker=ticker,
        capacity_1=capacity_1,
        capacity_2=capacity_2,
        ship_preset=ship_preset,
    )
    response = global_formatter.format_service_result(result, "装载计算：\n")
    await fiqo_fit.finish(response)
