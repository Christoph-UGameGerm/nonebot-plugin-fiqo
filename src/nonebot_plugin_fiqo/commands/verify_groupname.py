from nonebot import logger
from arclet.alconna import Arparma
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import (
    At,
    Args,
    Option,
    Alconna,
    MultiVar,
    UniMessage,
    CommandMeta,
    on_alconna,
)
from nonebot.adapters.onebot.v11 import Bot as OB11Bot

from nonebot_plugin_fiqo.services import verify_groupname_service

from .permissions import SUPERUSER, get_group_member_info

fiqo_vg = on_alconna(
    Alconna(
        "vg",
        Args["member;?", At],
        Option("-n|--nickname", Args["nickname", MultiVar(str)]),
        meta=CommandMeta(
            description="[超级用户] 验证群成员的昵称是否包含游戏内用户名或公司代码",
            usage="/vg <@成员> 或 /vg -n <昵称>",
        ),
    ),
    permission=SUPERUSER,
)


@fiqo_vg.handle()
async def _(
    event: Event,
    bot: Bot,
    result: Arparma,
) -> None:
    user_nickname = None
    member = result.query[At]("member")
    nickname = result.query[tuple[str, ...]]("nickname")
    logger.info(f"Handling vg command with {member=}, {nickname=}")

    if member and isinstance(bot, OB11Bot):
        user_nickname = await get_group_member_info(
            bot, event.get_session_id(), member.target
        )
        logger.info(f"Fetched user nickname for {member.target=}: {user_nickname=}")
        user_nickname = user_nickname.get("card") if user_nickname else None
    else:
        user_nickname = " ".join(nickname).removeprefix("@") if nickname else None
    if not user_nickname:
        await fiqo_vg.finish("请提供需要验证的昵称或 @ 成员")
    report = await verify_groupname_service.get_verification_report(user_nickname)

    if isinstance(member, At):
        target = At("user", member.target)
    else:
        target = At("user", event.get_user_id())
    response = (
        UniMessage.text("验证结果：\n") + UniMessage(target) + UniMessage.text("请查收")
    )
    await fiqo_vg.finish(response + "\n" + report)
