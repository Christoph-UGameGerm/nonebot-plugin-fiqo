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

fiqo_co = on_alconna(
    Alconna(
        "co",
        Args["member;?", At]["company_code;?", str],
        meta=CommandMeta(
            description="[普通用户] 查询公司代码对应的用户与公司信息",
            usage="/co <公司代码> 或 /co <@成员>",
            example="/co UTC，/co @某成员",
        ),
    ),
    permission=NORMALUSER,
)


@fiqo_co.handle()
async def _(event: Event, bot: Bot, param: Arparma) -> None:
    member = param.query[At]("member")
    company_code = param.query[str]("company_code")

    if member and isinstance(bot, OB11Bot):
        member_info = await get_group_member_info(
            bot, event.get_session_id(), member.target
        )
        nickname = (
            member_info.get("card") or member_info.get("nickname")
            if member_info
            else None
        )
        company_code = (
            await uinfo_service.resolve_company_code_from_nickname(nickname)
            if nickname
            else None
        ) or nickname

    if not company_code:
        await fiqo_co.finish("请提供公司代码或 @ 成员")

    result = await execute_tasks(
        [info_service.get_user_and_company_info(company_code=company_code.upper())]
    )
    response = global_formatter.format_service_result(
        result,
        header="用户与公司查询结果：\n",
    )
    await fiqo_co.finish(response)
