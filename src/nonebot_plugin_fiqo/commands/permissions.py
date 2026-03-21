from typing import Any

from nonebot.adapters import Bot, Event
from nonebot.permission import Permission
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot.adapters.onebot.v11 import Bot as OB11Bot

from nonebot_plugin_fiqo.config import plugin_config


async def get_group_member_info(
    bot: OB11Bot, group_id: str, user_id: str
) -> dict[str, Any] | None:
    try:
        return await bot.get_group_member_info(
            group_id=int(group_id.split("_")[1]), user_id=int(user_id)
        )
    except IndexError:
        return None


async def group_admin(bot: OB11Bot, event: Event) -> bool:
    try:
        user_id = event.get_user_id()
        group_id = event.get_session_id()
    except ValueError:
        return False
    if not group_id or not user_id:
        return False
    info = await get_group_member_info(bot, group_id, user_id)
    return info is not None and info.get("role", "member") in ("owner", "admin")


async def has_group_title(bot: OB11Bot, event: Event) -> bool:
    try:
        user_id = event.get_user_id()
        group_id = event.get_session_id()
    except ValueError:
        return False
    if not group_id or not user_id:
        return False
    info = await get_group_member_info(bot, group_id, user_id)
    return info is not None and bool(info.get("title"))


async def group_level_equal_or_above(bot: OB11Bot, event: Event) -> bool:
    try:
        user_id = event.get_user_id()
        group_id = event.get_session_id()
    except ValueError:
        return False
    if not group_id or not user_id:
        return False
    info = await get_group_member_info(bot, group_id, user_id)
    if info is None:
        return False
    return int(info.get("level", "0")) >= plugin_config.users.group_level_threshold


def admin(bot: Bot, event: Event) -> bool:
    try:
        user_id = event.get_user_id()
    except ValueError:
        return False
    return (
        f"{bot.adapter.get_name().split(maxsplit=1)[0].lower()}:{user_id}"
        in plugin_config.users.admin
    )


def super_user(bot: Bot, event: Event) -> bool:
    try:
        user_id = event.get_user_id()
    except ValueError:
        return False
    return (
        f"{bot.adapter.get_name().split(maxsplit=1)[0].lower()}:{user_id}"
        in plugin_config.users.superusers
    )


def test_user(bot: Bot, event: Event) -> bool:
    try:
        user_id = event.get_user_id()
    except ValueError:
        return False
    return (
        f"{bot.adapter.get_name().split(maxsplit=1)[0].lower()}:{user_id}"
        in plugin_config.users.testusers
    )


fiqo_perm = on_alconna(
    Alconna(
        "perm",
        meta=CommandMeta(
            description="[无权限要求] 查看权限组",
            usage="/perm",
        ),
    )
)


@fiqo_perm.handle()
async def _(event: Event, bot: Bot) -> None:
    groups = []

    is_group_admin = False
    group_title_exists = False
    group_level_enough = False

    if isinstance(bot, OB11Bot):
        try:
            user_id = event.get_user_id()
            group_id = event.get_session_id()
            if group_id and user_id:
                info = await get_group_member_info(bot, group_id, user_id)
                if info is not None:
                    is_group_admin = info.get("role", "member") in ("owner", "admin")
                    group_title_exists = bool(info.get("title"))
                    group_level_enough = (
                        int(info.get("level", "0"))
                        >= plugin_config.users.group_level_threshold
                    )
        except ValueError:
            pass

    in_superuser_whitelist = super_user(bot, event)
    in_testuser_whitelist = test_user(bot, event)
    is_admin = admin(bot, event)

    is_superuser = in_superuser_whitelist | is_group_admin | is_admin
    is_testuser = in_testuser_whitelist | is_superuser
    is_normaluser = (
        isinstance(bot, OB11Bot)
        and (is_group_admin or group_title_exists or group_level_enough)
    ) | is_testuser

    if is_admin:
        groups.append("开发组")
    if is_superuser:
        groups.append("超级用户" + ("，继承自开发组" if is_admin else ""))
        groups.append(f"  白名单：{'是' if in_superuser_whitelist else '否'}")
        groups.append(f"  群管理：{'是' if is_group_admin else '否'}")
    if is_testuser:
        groups.append("测试用户" + ("，继承自超级用户" if is_superuser else ""))
        groups.append(f"  白名单：{'是' if in_testuser_whitelist else '否'}")
    if is_normaluser:
        groups.append("普通用户" + ("，继承自测试用户" if is_testuser else ""))
    groups.append(f"  群管理：{'是' if is_group_admin else '否'}")
    groups.append(f"  群头衔：{'有' if group_title_exists else '无'}")
    groups.append(f"  群等级：{'足够' if group_level_enough else '不足'}")

    response = (
        "您属于以下权限组：\n" + "\n".join([f"- {group}" for group in groups])
        if any(not g.startswith("  ") for g in groups)
        else "您不属于任何权限组。"
    )
    await fiqo_perm.finish(response)


GROUPADMIN = Permission(group_admin)
GROUPTITLE = Permission(has_group_title)
GROUPLEVEL = Permission(group_level_equal_or_above)

ADMIN = Permission(admin)
SUPERUSER = (Permission(super_user) | GROUPADMIN) | ADMIN
TESTUSER = Permission(test_user) | SUPERUSER
NORMALUSER = (GROUPADMIN | GROUPLEVEL | GROUPTITLE) | TESTUSER
