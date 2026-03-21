from arclet.alconna import MultiVar
from nonebot_plugin_alconna import (
    Args,
    Match,
    Query,
    Option,
    Alconna,
    CommandMeta,
    on_alconna,
    store_true,
)

from nonebot_plugin_fiqo.utils import (
    execute_batch,
    global_formatter,
)
from nonebot_plugin_fiqo.services import fio_service

from .extensions import OB11GroupFwdExtension
from .permissions import NORMALUSER

fiqo_material = on_alconna(
    Alconna(
        "mat",
        Args["ticker#物品代码", MultiVar(str)],
        Option(
            "-r|--recipes", help_text="同时查询配方", action=store_true, default=False
        ),
        meta=CommandMeta(
            description="[普通用户] 查询材料信息",
            usage="/mat <ticker>",
            example="/mat RAT",
        ),
    ),
    extensions=[OB11GroupFwdExtension()],
    permission=NORMALUSER,
)


@fiqo_material.handle()
async def _(
    ticker: Match[tuple[str, ...]], recipes: Query = Query("recipes.value")
) -> None:
    ticker_list = [t.strip().upper() for t in ticker.result]
    if recipes.available and recipes.result:
        result = await execute_batch(
            ticker_list, fio_service.get_material_info_with_recipes
        )
    else:
        result = await execute_batch(ticker_list, fio_service.get_material_info)
    response = global_formatter.format_service_result(result, "材料信息：\n")
    await fiqo_material.finish(response)
