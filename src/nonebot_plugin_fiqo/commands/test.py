from nonebot import logger
from nonebot_plugin_alconna import (
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
        meta=CommandMeta(
            description="测试命令",
            hide=True,
        ),
    ),
    extensions=[OB11GroupFwdExtension(0, 0)],
    permission=ADMIN,
)


@fiqo_test.handle()
async def _(message: str, img: Image | None):
    logger.info(f"Received test command with message: {message}")
    response = UniMessage(message)
    if img:
        response += img
    await fiqo_test.send(response)
    raise RuntimeError("This is a test error to check error handling.")
