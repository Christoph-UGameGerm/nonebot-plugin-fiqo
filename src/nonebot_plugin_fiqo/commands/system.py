from arclet.alconna import StrMulti
from nonebot_plugin_alconna import Args, Alconna, CommandMeta, on_alconna

from nonebot_plugin_fiqo.utils import execute_batch, global_formatter
from nonebot_plugin_fiqo.services import info_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_system = on_alconna(
    Alconna(
        "sysi",
        Args["query#恒星系名称/ID", StrMulti],
        meta=CommandMeta(
            description="[普通用户] 查询恒星系信息",
            usage="/sysi <恒星系名称或ID>",
            example="/sysi benten，/sysi VH-331",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_system.handle()
async def _(query: str) -> None:
    query_list = [q.strip() for q in query.split()]
    result = await execute_batch(query_list, info_service.get_system_info)
    response = global_formatter.format_service_result(result, "恒星系信息：\n")
    await fiqo_system.finish(response)
