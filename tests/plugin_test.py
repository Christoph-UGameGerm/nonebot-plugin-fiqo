import pytest
from fake import fake_group_message_event_v11
from nonebug import App


@pytest.mark.asyncio
async def test_perm(app: App):
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot
    from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

    event = fake_group_message_event_v11(message="perm")
    try:
        from nonebot_plugin_fiqo.commands.permissions import fiqo_perm
    except ImportError as e:
        pytest.fail(f"Module permissions not found: {e}")

    async with app.test_matcher(fiqo_perm) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        ctx.receive_event(bot, event)

        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 87654321, "user_id": 12345678},
            {"role": "member", "title": "", "level": "1"},
        )

        ctx.should_call_send(event, "您不属于任何权限组。", result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_mat(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot, Message
    from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

    event = fake_group_message_event_v11(message="mat 123")
    try:
        from nonebot_plugin_fiqo.commands.material import fiqo_material
    except ImportError as e:
        pytest.fail(f"Module material not found: {e}")

    # Mock FIOService.get_material_info
    @staticmethod
    async def mock_get_material_info(ticker: str) -> str:
        return f"材料 {ticker}：Test Material\n描述：This is a test material."

    from nonebot_plugin_fiqo.services.fio_service import FIOService

    monkeypatch.setattr(FIOService, "get_material_info", mock_get_material_info)

    async with app.test_matcher(fiqo_material) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        ctx.receive_event(bot, event)

        # Mock concurrent permission checks (3 conditions in NORMALUSER)
        for _ in range(3):
            ctx.should_call_api(
                "get_group_member_info",
                {"group_id": 87654321, "user_id": 12345678},
                {"role": "admin", "title": "", "level": "1"},
            )

        ctx.should_call_send(
            event,
            Message(
                "材料信息：\n材料 123：Test Material\n描述：This is a test material."
            ),
            result=None,
            bot=bot,
        )
        ctx.should_finished()
