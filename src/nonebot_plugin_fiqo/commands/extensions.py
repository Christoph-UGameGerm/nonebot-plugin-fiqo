from nonebot.adapters import Bot, Event
from nonebot.exception import FinishedException
from nonebot_plugin_alconna import Text, Extension, UniMessage
from nonebot.adapters.onebot.v11 import Bot as OB11Bot
from nonebot.adapters.onebot.v11 import Event as OB11Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent as OB11GroupMessageEvent
from nonebot.adapters.onebot.v11 import PrivateMessageEvent as OB11PrivateMessageEvent
from nonebot_plugin_alconna.extension import TM
from nonebot.adapters.onebot.v11.exception import ActionFailed

from nonebot_plugin_fiqo.config import plugin_config


class OB11GroupFwdExtension(Extension):
    def __init__(
        self,
        line_no_limit: int = plugin_config.format.single_response_line_limit,
        char_limit: int = plugin_config.format.single_response_char_limit,
    ) -> None:
        self.line_no_limit = line_no_limit
        self.char_limit = char_limit

    @property
    def priority(self) -> int:
        return 100

    @property
    def id(self) -> str:
        return "OB11GroupFwdExtension"

    async def send_wrapper(self, bot: Bot, event: Event, send: TM) -> TM:
        if (
            not isinstance(bot, OB11Bot)
            or not isinstance(event, OB11Event)
            or not isinstance(send, UniMessage)
        ):
            return send

        total_lines = 0
        total_chars = 0
        msg_plain_text = send.extract_plain_text()
        for line in msg_plain_text.splitlines():
            total_lines += 1
            total_chars += len(line)
        if (
            total_lines > self.line_no_limit
            or total_chars > self.char_limit
            or not send.only(Text)
        ):
            messages = await send.export(bot)
            messages = [
                {
                    "type": "node",
                    "data": {
                        "user_id": event.self_id,
                        "nickname": "FIQO",
                        "content": segment,
                    },
                }
                for segment in messages
            ]
            try:
                if isinstance(event, OB11PrivateMessageEvent):
                    await bot.send_private_forward_msg(
                        user_id=event.user_id, messages=messages
                    )
                elif isinstance(event, OB11GroupMessageEvent):
                    await bot.send_forward_msg(
                        group_id=event.group_id, messages=messages
                    )
            except ActionFailed:
                return send
            raise FinishedException
        return send
