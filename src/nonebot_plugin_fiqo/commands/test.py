from nonebot import logger
from nonebot_plugin_alconna import (
    Args,
    Image,
    Alconna,
    UniMessage,
    CommandMeta,
    on_alconna,
)

from nonebot_plugin_fiqo.commands.extensions import (
    OB11GroupFwdExtension,
)

from .permissions import ADMIN

fiqo_test = on_alconna(
    Alconna(
        "test",
        Args["message", str],
        Args["img?", Image],
        meta=CommandMeta(
            description="测试命令",
            hide=True,
        ),
    ),
    extensions=[OB11GroupFwdExtension(0, 0)],
    permission=ADMIN,
)

@fiqo_test.handle()
async def _2(message: str):
    await _(message, None)


@fiqo_test.handle()
async def _(message: str, img: Image | None):
    logger.info(f"Received test command with message: {message}")
    response = UniMessage(message)
    if img:
        response += img

    await fiqo_test.finish(
        response
    )
