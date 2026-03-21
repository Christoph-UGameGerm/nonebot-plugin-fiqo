import asyncio

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

from nonebot_plugin_fiqo.utils import (
    global_formatter,
    analyze_nickname_entities,
)
from nonebot_plugin_fiqo.services import fio_service

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

    if symbol_warning := "丨" in user_nickname:
        user_nickname = user_nickname.replace("丨", " | ")
    nickname_fields = global_formatter.clean_and_partition_group_nickname(user_nickname)

    tasks = [
        fio_service.identify_user_company_token(f, i)
        for (i, f) in enumerate(nickname_fields)
    ]
    service_result = await asyncio.gather(*tasks)

    best_dto, report_lines = analyze_nickname_entities(service_result)

    if isinstance(member, At):
        target = At("user", member.target)
    else:
        target = At("user", event.get_user_id())
    response = (
        UniMessage.text("验证结果：\n") + UniMessage(target) + UniMessage.text("请查收")
    )

    warning_header = [
        "\n分隔符警告：昵称中包含 '丨'，建议使用两侧带空格的 '|' 作为分隔符。"
        if symbol_warning
        else None
    ]
    warning_header = "\n".join([h for h in warning_header if h]) + "\n"
    final_header = (
        response
        + warning_header
        + "\n".join(report_lines)
        + "\n"
        + global_formatter.format_user_company_key_info(best_dto)
        if best_dto
        else response + "\n暂无置信度足够的游戏内用户或公司信息"
    )

    await fiqo_vg.finish(final_header)
