import asyncio

import pytest
from fake import fake_group_message_event_v11
from nonebug import App


@pytest.mark.asyncio
async def test_base_client_reuses_inflight_request(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import base_client as base_client_module
    from nonebot_plugin_fiqo.exceptions import ResourceNotFoundError
    from nonebot_plugin_fiqo.api.base_client import BaseClient

    class DummyNotFoundError(ResourceNotFoundError):
        def __init__(self) -> None:
            super().__init__("dummy", "dummy")

    client = BaseClient("https://example.com", timeout=10)
    perform_calls = 0
    cache_set_calls = 0

    async def mock_cache_get(key: str, model: object) -> None:
        return None

    async def mock_cache_set(key: str, value: int, ttl: int) -> None:
        nonlocal cache_set_calls
        cache_set_calls += 1

    async def mock_perform_request(
        endpoint: str,
        model: object,
        not_found_error: ResourceNotFoundError,
        params: dict | None = None,
    ) -> int:
        nonlocal perform_calls
        perform_calls += 1
        await asyncio.sleep(0)
        return 1

    monkeypatch.setattr(base_client_module.disk_cache, "get", mock_cache_get)
    monkeypatch.setattr(base_client_module.disk_cache, "set", mock_cache_set)
    monkeypatch.setattr(client, "_perform_request", mock_perform_request)

    results = await asyncio.gather(
        client.request(
            ("dummy:key", int), "/dummy", None, DummyNotFoundError(), ttl=60
        ),
        client.request(
            ("dummy:key", int), "/dummy", None, DummyNotFoundError(), ttl=60
        ),
    )

    await client.close()

    assert results == [1, 1]
    assert perform_calls == 1
    assert cache_set_calls == 1


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

    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    monkeypatch.setattr(GameInfoService, "get_material_info", mock_get_material_info)

    async with app.test_matcher(fiqo_material) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

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
        ctx.receive_event(bot, event)
        ctx.should_finished()


def make_planner_planet(**overrides):
    from nonebot_plugin_fiqo.models import PlannerPlanetDTO

    data = {
        "natural_id": "VH-331a",
        "name": "Katoa",
        "system_id": "f2f57766ebaca9d69efae41ccf4d8853",
        "faction": "IC1",
        "has_rock_surface": True,
        "fertility": 0.5,
        "gravity": 1.02,
        "temperature": 24.0,
        "pressure": 1.03,
        "has_adm": True,
        "has_cogc": False,
        "has_localmarket": True,
        "has_warehouse": True,
        "has_shipyard": False,
        "cogc_status": None,
        "active_cogc_program_type": None,
        "resources": [],
        "cogc_programs": [],
    }
    data.update(overrides)
    return PlannerPlanetDTO(**data)


def install_mock_system_info(
    monkeypatch: pytest.MonkeyPatch,
    *,
    natural_id: str = "VH-331",
    name: str = "Vallis Hydri",
    system_id: str = "f2f57766ebaca9d69efae41ccf4d8853",
):
    from nonebot_plugin_fiqo.api import fio_client
    from nonebot_plugin_fiqo.models import SystemDTO

    async def mock_get_system_info(system_id_or_name: str):
        assert system_id_or_name == system_id
        return SystemDTO(
            natural_id=natural_id,
            name=name,
        )

    monkeypatch.setattr(fio_client, "get_system_info", mock_get_system_info)


@pytest.mark.asyncio
async def test_planet_dto_uses_planner_data(monkeypatch: pytest.MonkeyPatch):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.models import PlanetResourceDTO
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return [
            make_planner_planet(
                resources=[
                    PlanetResourceDTO(
                        type="LIQUID",
                        factor=0.8,
                        ticker="H2O",
                        daily_extraction=123.45,
                        max_extraction_in_world=999.0,
                    )
                ]
            )
        ]

    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    install_mock_system_info(monkeypatch)

    dto = await GameInfoService.get_planet_dto("Katoa")

    assert dto.natural_id == "VH-331a"
    assert dto.name == "Katoa"
    assert dto.system_display_name == "Vallis Hydri (VH-331)"
    assert dto.resources
    assert dto.resources[0].ticker == "H2O"
    assert dto.fertility_percent == pytest.approx(115.15)


def test_planet_dto_fertility_percent_handles_non_fertile_planet():
    from nonebot_plugin_fiqo.models import PlanetDTO

    dto = PlanetDTO(
        natural_id="VH-331a",
        name="Katoa",
        system_id="f2f57766ebaca9d69efae41ccf4d8853",
        faction="IC1",
        has_rock_surface=True,
        fertility=-1,
        gravity=1.02,
        temperature=24.0,
        pressure=1.03,
        has_adm=True,
        has_cogc=False,
        has_localmarket=True,
        has_warehouse=True,
        has_shipyard=False,
        cogc_status=None,
    )

    assert dto.fertility_percent == 0


@pytest.mark.asyncio
async def test_planet_dto_raises_not_found_on_empty_planner_result(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.exceptions import PlanetNotFoundError
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return []

    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)

    with pytest.raises(PlanetNotFoundError):
        await GameInfoService.get_planet_dto("Katoa")


@pytest.mark.asyncio
async def test_planet_dto_merge_with_none_cogc_program_type(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.models import CoGCProgramDTO
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return [
            make_planner_planet(
                has_cogc=True,
                cogc_status="ACTIVE",
                cogc_programs=[
                    CoGCProgramDTO(
                        type=None,
                        start_epoch_ms=0,
                        end_epoch_ms=4102444800000,
                    )
                ],
            )
        ]

    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    install_mock_system_info(monkeypatch)

    dto = await GameInfoService.get_planet_dto("Katoa")

    assert dto.cogc_program is not None
    assert dto.cogc_program.type is None


@pytest.mark.asyncio
async def test_planet_dto_prefers_active_cogc_program_type(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.models import CoGCProgramDTO
    from nonebot_plugin_fiqo.services.i18n_service import i18n_service
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return [
            make_planner_planet(
                has_cogc=True,
                cogc_status="ACTIVE",
                active_cogc_program_type="OLDER",
                cogc_programs=[
                    CoGCProgramDTO(
                        type="OLDER",
                        start_epoch_ms=1700000000000,
                        end_epoch_ms=4102444800000,
                    ),
                    CoGCProgramDTO(
                        type="NEWER",
                        start_epoch_ms=1750000000000,
                        end_epoch_ms=4102444800000,
                    ),
                ],
            )
        ]

    async def mock_get_cogc_program_i18n_name(program_name: str) -> str:
        return program_name

    async def mock_get_cogc_i18n_status(status: str) -> str:
        assert status == "ACTIVE"
        return "已生效"

    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    monkeypatch.setattr(
        i18n_service, "get_cogc_program_i18n_name", mock_get_cogc_program_i18n_name
    )
    monkeypatch.setattr(i18n_service, "get_cogc_i18n_status", mock_get_cogc_i18n_status)
    install_mock_system_info(monkeypatch)

    dto = await GameInfoService.get_planet_dto("Katoa")

    assert dto.cogc_status == "已生效"
    assert dto.cogc_program is not None
    assert dto.cogc_program.type == "OLDER"


@pytest.mark.asyncio
async def test_planet_dto_keeps_latest_active_cogc_program(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.models import CoGCProgramDTO
    from nonebot_plugin_fiqo.services.i18n_service import i18n_service
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return [
            make_planner_planet(
                has_cogc=True,
                cogc_status="ACTIVE",
                active_cogc_program_type="MISSING",
                cogc_programs=[
                    CoGCProgramDTO(
                        type="OLDER",
                        start_epoch_ms=1700000000000,
                        end_epoch_ms=4102444800000,
                    ),
                    CoGCProgramDTO(
                        type="NEWER",
                        start_epoch_ms=1750000000000,
                        end_epoch_ms=4102444800000,
                    ),
                ],
            )
        ]

    async def mock_get_cogc_program_i18n_name(program_name: str) -> str:
        return program_name

    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    monkeypatch.setattr(
        i18n_service, "get_cogc_program_i18n_name", mock_get_cogc_program_i18n_name
    )
    install_mock_system_info(monkeypatch)

    dto = await GameInfoService.get_planet_dto("Katoa")

    assert dto.cogc_program is not None
    assert dto.cogc_program.type == "NEWER"


@pytest.mark.asyncio
async def test_planet_dto_keeps_original_cogc_program_name_on_i18n_error(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.models import CoGCProgramDTO
    from nonebot_plugin_fiqo.exceptions import I18nFetchError
    from nonebot_plugin_fiqo.services.i18n_service import i18n_service
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return [
            make_planner_planet(
                has_cogc=True,
                cogc_status="ACTIVE",
                active_cogc_program_type="ORIGINAL",
                cogc_programs=[
                    CoGCProgramDTO(
                        type="ORIGINAL",
                        start_epoch_ms=1700000000000,
                        end_epoch_ms=4102444800000,
                    )
                ],
            )
        ]

    async def mock_get_cogc_program_i18n_name(program_name: str) -> str:
        raise I18nFetchError(program_name)

    async def mock_get_cogc_i18n_status(status: str) -> str:
        raise I18nFetchError(status)

    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    monkeypatch.setattr(
        i18n_service, "get_cogc_program_i18n_name", mock_get_cogc_program_i18n_name
    )
    monkeypatch.setattr(i18n_service, "get_cogc_i18n_status", mock_get_cogc_i18n_status)
    install_mock_system_info(monkeypatch)

    dto = await GameInfoService.get_planet_dto("Katoa")

    assert dto.cogc_status == "ACTIVE"
    assert dto.cogc_program is not None
    assert dto.cogc_program.type == "ORIGINAL"
