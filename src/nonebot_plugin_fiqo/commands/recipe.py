from arclet.alconna import StrMulti
from nonebot_plugin_alconna import Args, Alconna, CommandMeta, on_alconna

from nonebot_plugin_fiqo.utils import (
    execute_batch,
    global_formatter,
)
from nonebot_plugin_fiqo.services import fio_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_recipe = on_alconna(
    Alconna(
        "recipe",
        Args["ticker#物品代码", StrMulti],
        meta=CommandMeta(
            description="[普通用户] 查询配方信息",
            usage="/recipe <ticker>",
            example="/recipe RAT",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)

@fiqo_recipe.handle()
async def _(ticker: str) -> None:
    ticker_list = [t.strip().upper() for t in ticker.split()]
    result = await execute_batch(ticker_list, fio_service.get_recipe_info)
    response = global_formatter.format_service_result(result, "配方信息：\n")
    await fiqo_recipe.finish(response)
