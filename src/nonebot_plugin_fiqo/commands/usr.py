from arclet.alconna import Arparma
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import (
    At,
    Args,
    Alconna,
    CommandMeta,
    on_alconna,
)
from nonebot.adapters.onebot.v11 import Bot as OB11Bot

from nonebot_plugin_fiqo.utils import execute_tasks, global_formatter
from nonebot_plugin_fiqo.services import info_service, uinfo_service

from .permissions import NORMALUSER, get_group_member_info

fiqo_usr = on_alconna(
    Alconna(
        "usr",
        Args["member;?", At]["username;?", str],
        meta=CommandMeta(
            description="[普通用户] 查询用户名对应的用户与公司信息",
            usage="/usr <用户名> 或 /usr <@成员>",
            example="/usr UGameGerm，/usr @某成员",
        ),
    ),
    permission=NORMALUSER,
)


@fiqo_usr.handle()
async def _(event: Event, bot: Bot, param: Arparma) -> None:
    member = param.query[At]("member")
    username = param.query[str]("username")

    if member and isinstance(bot, OB11Bot):
        member_info = await get_group_member_info(
            bot, event.get_session_id(), member.target
        )
        nickname = (
            member_info.get("card") or member_info.get("nickname")
            if member_info
            else None
        )
        username = (
            await uinfo_service.resolve_username_from_nickname(nickname)
            if nickname
            else None
        ) or nickname

    if not username:
        await fiqo_usr.finish("请提供用户名或 @ 成员")

    result = await execute_tasks(
        [info_service.get_user_and_company_info(username=username)]
    )
    response = global_formatter.format_service_result(
        result,
        header="用户与公司查询结果：\n",
    )
    await fiqo_usr.finish(response)
