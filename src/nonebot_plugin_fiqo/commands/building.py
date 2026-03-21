from arclet.alconna import StrMulti
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, on_alconna

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.services import fio_service
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.utils import (
    execute_batch,
    global_formatter,
)

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_building = on_alconna(
    Alconna(
        "bui",
        Args["ticker#建筑代码", StrMulti],
        meta=CommandMeta(
            description="[普通用户] 查询建筑信息",
            usage="/bui <ticker>",
            example="/bui FRM",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)

@fiqo_building.handle()
async def _(ticker: str) -> None:
    ticker_list = [t.strip().upper() for t in ticker.split()]
    result = await execute_batch(ticker_list, fio_service.get_building_info)
    response = global_formatter.format_service_result(result, "建筑信息：\n")
    await fiqo_building.finish(response)
