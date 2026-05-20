from arclet.alconna import StrMulti
from nonebot_plugin_alconna import Args, Alconna, CommandMeta, on_alconna

from nonebot_plugin_fiqo.utils import (
    execute_batch,
    global_formatter,
)
from nonebot_plugin_fiqo.services import info_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_planet = on_alconna(
    Alconna(
        "pli",
        Args["query#行星名称/ID", StrMulti],
        meta=CommandMeta(
            description="[普通用户] 查询行星信息",
            usage="/pli <行星名称或ID>",
            example="/pli Katoa，/pli VH-331a",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_planet.handle()
async def _(query: str) -> None:
    query_list = [q.strip() for q in query.split()]
    result = await execute_batch(query_list, info_service.get_planet_info)
    response = global_formatter.format_service_result(result, "行星信息：\n")
    await fiqo_planet.finish(response)
