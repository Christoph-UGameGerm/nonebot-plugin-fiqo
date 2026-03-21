from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.utils import disk_cache

from .permissions import ADMIN

fiqo_clearcache = on_alconna(
    Alconna(
        "clearcache",
        meta=CommandMeta(
            description="清除所有缓存",
            usage="/clearcache",
            hide=True,
        ),
    ),
    permission=ADMIN,
)


@fiqo_clearcache.handle()
async def _() -> None:
    await disk_cache.clear_all()
    await fiqo_clearcache.finish("已清除所有缓存")
