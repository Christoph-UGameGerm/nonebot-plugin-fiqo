from nonebot import logger
from nonebot.adapters import Bot
from nonebot.adapters import console as console_adapter
from nonebot.adapters.onebot import v11 as onebot_v11_adapter
from nonebot_plugin_alconna import UniMessage

# Supported Adapters
SUPPORTED_BOTS = console_adapter.Bot | onebot_v11_adapter.Bot
SUPPORTED_MSG_EVENTS = console_adapter.MessageEvent | onebot_v11_adapter.MessageEvent
SUPPORT_FWD_PRIVATE_MSG_EVENT = \
    onebot_v11_adapter.PrivateMessageEvent
SUPPORT_FWD_GROUP_MSG_EVENT = \
    onebot_v11_adapter.GroupMessageEvent

# Helper Functions
async def try_send_grouped_forward_msg(
    event: SUPPORTED_MSG_EVENTS,
    bot: Bot,
    message: UniMessage) -> None:
    """
    Docstring for try_send_grouped_forward_msg

    :param event: Event of the context in which the message responds to.
    :type event: nonebot.adapters.Event
    :param bot: Bot instance to send the message.
    :type bot: nonebot.adapters.Bot
    :param message: Alconna UniMessage to be sent. This function will\
        attempt to construct a grouped version of the message
    :type message: UniMessage
    """
    logger.info("Attempting to send grouped forward message.")
    try:
        # Try to send grouped forward message through OneBot v11 Adapter
        grouped_message = [
            onebot_v11_adapter.MessageSegment(
                type="node",
                data={
                    "user_id": str(event.self_id),
                    "nickname": "FIQO",
                    "content": await message.export()
                }
            )
        ]
        if isinstance(event, SUPPORT_FWD_GROUP_MSG_EVENT):
            logger.info("Sending grouped forward msg to group"
                        "via OneBot v11 Adapter.")
            await bot.send_forward_msg(
                group_id=event.group_id,
                messages=grouped_message
            )
        elif isinstance(event, SUPPORT_FWD_PRIVATE_MSG_EVENT):
            logger.info("Sending grouped forward msg to private user"
                        "via OneBot v11 Adapter.")
            await bot.send_forward_msg(
                user_id=event.user_id,
                messages=grouped_message
            )
        else:
            logger.warning("Event type not supported for grouped forward message."
                           "Sending as a normal message.")
            await bot.send(
                event=event,
                message=await message.export()
        )
    except Exception as e:
        logger.error(f"Unexpected error occurred while sending message: {e}")
        raise
    logger.info("Message sent successfully.")

class MessageFormatHelper:
    """
    Helper class for constructing formal formatted messages.
    """
    def __init__(self) -> None:
        self.head_msg_list: list[UniMessage] = []
        self.core_msg_list: list[UniMessage] = []
        self.tail_msg_list: list[UniMessage] = []

    def add_head(self, msg: UniMessage | str) -> None:
        if isinstance(msg, str):
            msg = UniMessage.text(msg)
        self.head_msg_list.append(msg)

    def add_core(self, msg: UniMessage | str) -> None:
        if isinstance(msg, str):
            msg = UniMessage.text(msg)
        self.core_msg_list.append(msg)

    def add_tail(self, msg: UniMessage | str) -> None:
        if isinstance(msg, str):
            msg = UniMessage.text(msg)
        self.tail_msg_list.append(msg)

    def construct_formal_response(
        self,
        response_separator: UniMessage | str = UniMessage.text("-------------------")
    ) -> UniMessage:
        """
        Construct a formal formatted response message\
            by combining messages from multiple parts with separators.
        Separators will be added between head and core,\
            in between each core message,\
            and between core and tail.

        :param response_separator: The separator message to be inserted.
        :type response_separator: UniMessage | str
        :return: The combined formal response message
        :rtype: UniMessage[Any]
        """
        newline = UniMessage.text("\n")
        response = UniMessage.text("")
        if isinstance(response_separator, str):
            response_separator = UniMessage.text(response_separator)
        for index, head_msg in enumerate(self.head_msg_list):
            if index > 0:
                response += newline
            response += head_msg
        if self.core_msg_list:
            response += newline
            response += response_separator
        for index, core_msg in enumerate(self.core_msg_list):
            if index > 0:
                response += newline
                response += response_separator
            response += newline
            response += core_msg
        if self.tail_msg_list:
            response += newline
            response += response_separator
        for tail_msg in self.tail_msg_list:
            response += newline
            response += tail_msg
        return response
