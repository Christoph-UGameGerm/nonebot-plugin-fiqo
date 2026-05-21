import asyncio
from datetime import datetime, timezone

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


@pytest.mark.asyncio
async def test_fit(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot, Message
    from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

    event = fake_group_message_event_v11(message="fit AEF 3000t 1000m")
    try:
        from nonebot_plugin_fiqo.commands.fit import fiqo_fit
    except ImportError as e:
        pytest.fail(f"Module fit not found: {e}")

    @staticmethod
    async def mock_get_fit_result(
        ticker: str | None,
        capacity_1: str | None = None,
        capacity_2: str | None = None,
        ship_preset: str | None = None,
    ):
        from nonebot_plugin_fiqo.models import ServiceResult

        assert ticker == "AEF"
        assert capacity_1 == "3000t"
        assert capacity_2 == "1000m"
        assert ship_preset is None
        return ServiceResult(contents=["200 AEF\n剩余重量 2000.00t"])

    from nonebot_plugin_fiqo.services.fit_service import FitService

    monkeypatch.setattr(FitService, "get_fit_result", mock_get_fit_result)

    async with app.test_matcher(fiqo_fit) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        for _ in range(3):
            ctx.should_call_api(
                "get_group_member_info",
                {"group_id": 87654321, "user_id": 12345678},
                {"role": "admin", "title": "", "level": "1"},
            )

        ctx.should_call_send(
            event,
            Message("装载计算：\n200 AEF\n剩余重量 2000.00t"),
            result=None,
            bot=bot,
        )
        ctx.receive_event(bot, event)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_co(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot, Message
    from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

    event = fake_group_message_event_v11(message="co IC1")
    try:
        from nonebot_plugin_fiqo.commands.co import fiqo_co
    except ImportError as e:
        pytest.fail(f"Module co not found: {e}")

    @staticmethod
    async def mock_get_user_and_company_info(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str:
        assert username is None
        assert company_code == "IC1"
        assert company_name is None
        return "公司：Insitor Cooperative\n代码：IC1"

    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    monkeypatch.setattr(
        GameInfoService, "get_user_and_company_info", mock_get_user_and_company_info
    )

    async with app.test_matcher(fiqo_co) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        for _ in range(3):
            ctx.should_call_api(
                "get_group_member_info",
                {"group_id": 87654321, "user_id": 12345678},
                {"role": "admin", "title": "", "level": "1"},
            )

        ctx.should_call_send(
            event,
            Message("用户与公司查询结果：\n公司：Insitor Cooperative\n代码：IC1"),
            result=None,
            bot=bot,
        )
        ctx.receive_event(bot, event)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_co_with_mention(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
    from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

    event = fake_group_message_event_v11(
        message=Message("co ") + MessageSegment.at(87654321)
    )
    try:
        from nonebot_plugin_fiqo.commands.co import fiqo_co
    except ImportError as e:
        pytest.fail(f"Module co not found: {e}")

    @staticmethod
    async def mock_resolve_company_code_from_nickname(nickname: str) -> str | None:
        assert nickname == "IC | UTC | TestUser"
        return "UTC"

    @staticmethod
    async def mock_get_user_and_company_info(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str:
        assert username is None
        assert company_code == "UTC"
        assert company_name is None
        return "公司：Universal Trading Coalition\n代码：UTC"

    from nonebot_plugin_fiqo.services.uinfo_service import UinfoService
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    monkeypatch.setattr(
        UinfoService,
        "resolve_company_code_from_nickname",
        staticmethod(mock_resolve_company_code_from_nickname),
    )
    monkeypatch.setattr(
        GameInfoService, "get_user_and_company_info", mock_get_user_and_company_info
    )

    async with app.test_matcher(fiqo_co) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        for _ in range(3):
            ctx.should_call_api(
                "get_group_member_info",
                {"group_id": 87654321, "user_id": 12345678},
                {"role": "admin", "title": "", "level": "1"},
            )

        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 87654321, "user_id": 87654321},
            {"card": "IC | UTC | TestUser", "nickname": "FallbackUser"},
        )

        ctx.should_call_send(
            event,
            Message(
                "用户与公司查询结果：\n公司：Universal Trading Coalition\n代码：UTC"
            ),
            result=None,
            bot=bot,
        )
        ctx.receive_event(bot, event)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_usr_with_mention(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
    from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter

    event = fake_group_message_event_v11(
        message=Message("usr ") + MessageSegment.at(87654321)
    )
    try:
        from nonebot_plugin_fiqo.commands.usr import fiqo_usr
    except ImportError as e:
        pytest.fail(f"Module usr not found: {e}")

    @staticmethod
    async def mock_resolve_username_from_nickname(nickname: str) -> str | None:
        assert nickname == "IC | UTC | TestUser"
        return "TestUser"

    @staticmethod
    async def mock_get_user_and_company_info(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str:
        assert username == "TestUser"
        assert company_code is None
        assert company_name is None
        return "用户：TestUser\n公司：TEST"

    from nonebot_plugin_fiqo.services.uinfo_service import UinfoService
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    monkeypatch.setattr(
        UinfoService,
        "resolve_username_from_nickname",
        staticmethod(mock_resolve_username_from_nickname),
    )
    monkeypatch.setattr(
        GameInfoService, "get_user_and_company_info", mock_get_user_and_company_info
    )

    async with app.test_matcher(fiqo_usr) as ctx:
        adapter = nonebot.get_adapter(OnebotV11Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        for _ in range(3):
            ctx.should_call_api(
                "get_group_member_info",
                {"group_id": 87654321, "user_id": 12345678},
                {"role": "admin", "title": "", "level": "1"},
            )

        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 87654321, "user_id": 87654321},
            {"card": "IC | UTC | TestUser", "nickname": "FallbackUser"},
        )

        ctx.should_call_send(
            event,
            Message("用户与公司查询结果：\n用户：TestUser\n公司：TEST"),
            result=None,
            bot=bot,
        )
        ctx.receive_event(bot, event)
        ctx.should_finished()


def test_fit_service_resolves_explicit_capacity_inputs():
    from nonebot_plugin_fiqo.services.fit_service import FitService

    result = FitService.resolve_fit_inputs("1000m", "3000t", None)

    assert result == (3000.0, 1000.0, None, None, None, None)


def test_fit_service_resolves_default_preset():
    from nonebot_plugin_fiqo.services.fit_service import FitService

    result = FitService.resolve_fit_inputs("WCB", None, None)

    assert result == (
        3000,
        1000,
        "WCB",
        "高负荷货舱套装",
        3000,
        1000,
    )


def test_fit_service_resolves_fitratio_compact_tokens():
    from nonebot_plugin_fiqo.services.fit_service import FitService

    result = FitService.resolve_fitratio_inputs(
        ["2AEF", "3MCG", "HSE", "3000t", "1000m"],
        None,
    )

    assert result == (
        [("AEF", 2), ("MCG", 3), ("HSE", 1)],
        3000.0,
        1000.0,
        None,
        None,
        None,
        None,
    )


def test_fit_service_resolves_fitratio_split_tokens_and_merges_duplicates():
    from nonebot_plugin_fiqo.services.fit_service import FitService

    result = FitService.resolve_fitratio_inputs(
        ["2", "AEF", "AEF", "3", "MCG", "WCB"],
        None,
    )

    assert result == (
        [("AEF", 3), ("MCG", 3)],
        3000,
        1000,
        "WCB",
        "高负荷货舱套装",
        3000,
        1000,
    )


def test_fit_service_rejects_fitratio_invalid_amount():
    from nonebot_plugin_fiqo.exceptions import EvaluationError
    from nonebot_plugin_fiqo.services.fit_service import FitService

    with pytest.raises(EvaluationError, match="无效的材料数量"):
        FitService.resolve_fitratio_inputs(["0AEF", "3000t", "1000m"], None)


def test_uinfo_service_resolves_company_code_from_nickname(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.models import UserAndCompanyDTO
    from nonebot_plugin_fiqo.services.uinfo_service import UinfoService
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    dto = UserAndCompanyDTO(
        user_id="user-1",
        company_id="company-1",
        username="TestUser",
        subscription_level="STANDARD",
        company_name="Universal Trading Coalition",
        company_code="UTC",
        rating="A",
        created_epoch_ms=0,
        faction="IC",
        bases=[],
        offices=[],
    )

    async def mock_identify_user_company_token(
        ticker: str,
        index: int,
    ) -> tuple[str, list[tuple[str, UserAndCompanyDTO | None]]]:
        if index == 0:
            return (ticker, [("派系", None)])
        if index == 1:
            return (ticker, [("公司代码", dto)])
        return (ticker, [("用户名", dto)])

    monkeypatch.setattr(
        GameInfoService,
        "identify_user_company_token",
        staticmethod(mock_identify_user_company_token),
    )

    result = asyncio.run(
        UinfoService.resolve_company_code_from_nickname("IC丨UTC丨TestUser")
    )

    assert result == "UTC"


def test_uinfo_service_resolves_username_from_nickname(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.models import UserAndCompanyDTO
    from nonebot_plugin_fiqo.services.uinfo_service import UinfoService
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    dto = UserAndCompanyDTO(
        user_id="user-1",
        company_id="company-1",
        username="TestUser",
        subscription_level="STANDARD",
        company_name="Universal Trading Coalition",
        company_code="UTC",
        rating="A",
        created_epoch_ms=0,
        faction="IC",
        bases=[],
        offices=[],
    )

    async def mock_identify_user_company_token(
        ticker: str,
        index: int,
    ) -> tuple[str, list[tuple[str, UserAndCompanyDTO | None]]]:
        if index == 0:
            return (ticker, [("派系", None)])
        if index == 1:
            return (ticker, [("公司代码", dto)])
        return (ticker, [("用户名", dto)])

    monkeypatch.setattr(
        GameInfoService,
        "identify_user_company_token",
        staticmethod(mock_identify_user_company_token),
    )

    result = asyncio.run(
        UinfoService.resolve_username_from_nickname("IC丨UTC丨TestUser")
    )

    assert result == "TestUser"


def test_recipe_dto_falls_back_when_standard_name_is_null():
    from nonebot_plugin_fiqo.models import RecipeDTO

    recipe = RecipeDTO.model_validate(
        {
            "StandardRecipeName": None,
            "BuildingTicker": "RIG",
            "RecipeName": "BAI-1",
            "DurationMs": 60000,
            "Inputs": [],
            "Outputs": [],
        }
    )

    assert recipe.string_representation == "RIG:BAI 1"


@pytest.mark.asyncio
async def test_user_and_company_dto_uses_fnar_planets_and_offices(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client, fnar_fio_client
    from nonebot_plugin_fiqo.models import UserAndCompanyDTO, FnarCompanyLookupDTO
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_user_and_company_info(
        username: str | None = None,
        company_name: str | None = None,
        company_code: str | None = None,
    ) -> UserAndCompanyDTO:
        assert username is None
        assert company_name is None
        assert company_code == "EVOV"
        return UserAndCompanyDTO(
            user_id="user-1",
            company_id="318869ca42834cc68ef07477d8310cee",
            username="EvoV",
            subscription_level="STANDARD",
            company_name="EvoV1980",
            company_code="EVOV",
            corporation_name="EvoSolo",
            corporation_code="EVSL",
            rating="A",
            created_epoch_ms=0,
            faction="IC",
            bases=[],
            offices=[],
        )

    async def mock_get_company_lookup(company_id: str) -> FnarCompanyLookupDTO:
        assert company_id == "318869ca42834cc68ef07477d8310cee"
        return FnarCompanyLookupDTO.model_validate(
            {
                "Name": "EvoV1980",
                "Code": "EVOV",
                "UserName": "EvoV",
                "CountryCode": "IC",
                "CorporationName": "EvoSolo",
                "CorporationCode": "EVSL",
                "OverallRating": "A",
                "Founded": "2022-04-22T21:25:51.435Z",
                "Planets": [
                    {
                        "PlanetName": "Lom Palanka",
                        "PlanetNaturalId": "QJ-684a",
                    },
                    {
                        "PlanetName": "IA-151a",
                        "PlanetNaturalId": "IA-151a",
                    },
                ],
                "Offices": [
                    {
                        "PlanetName": "ZV-307d",
                        "PlanetNaturalId": "ZV-307d",
                        "EndEpochMs": 0,
                    }
                ],
            }
        )

    monkeypatch.setattr(
        fio_client, "get_user_and_company_info", mock_get_user_and_company_info
    )
    monkeypatch.setattr(fnar_fio_client, "get_company_lookup", mock_get_company_lookup)

    dto = await GameInfoService.get_user_and_company_dto(company_code="EVOV")

    assert dto.base_counts == 2
    assert [base.natural_id for base in dto.bases] == ["IA-151a", "QJ-684a"]
    assert [office.natural_id for office in dto.offices] == ["ZV-307d"]


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
            meteoroid_density=0.0,
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


def test_planet_dto_environment_display_strings():
    from nonebot_plugin_fiqo.models import PlanetDTO

    low = PlanetDTO(
        natural_id="VH-331a",
        name="Katoa",
        system_id="f2f57766ebaca9d69efae41ccf4d8853",
        has_rock_surface=True,
        fertility=0.5,
        gravity=0.18,
        temperature=-42.3,
        pressure=0.12,
        has_adm=True,
        has_cogc=False,
        has_localmarket=True,
        has_warehouse=True,
        has_shipyard=False,
    )
    suitable = PlanetDTO(
        natural_id="VH-331a",
        name="Katoa",
        system_id="f2f57766ebaca9d69efae41ccf4d8853",
        has_rock_surface=False,
        fertility=0.5,
        gravity=1.02,
        temperature=16.25,
        pressure=1.01,
        has_adm=True,
        has_cogc=False,
        has_localmarket=True,
        has_warehouse=True,
        has_shipyard=False,
    )
    high = PlanetDTO(
        natural_id="VH-331a",
        name="Katoa",
        system_id="f2f57766ebaca9d69efae41ccf4d8853",
        has_rock_surface=True,
        fertility=0.5,
        gravity=2.83,
        temperature=96.4,
        pressure=2.31,
        has_adm=True,
        has_cogc=False,
        has_localmarket=True,
        has_warehouse=True,
        has_shipyard=False,
    )

    assert low.type_display == "岩质（MCG x4/面积）"
    assert low.gravity_display == "0.18（低重力，MGC x1/建筑）"
    assert low.temperature_display == "-42.30（低温，INS x10/面积）"
    assert low.pressure_display == "0.12（低压，SEA x1/面积）"

    assert suitable.type_display == "气态（AEF x面积/3）"
    assert suitable.gravity_display == "1.02（适宜）"
    assert suitable.temperature_display == "16.25（适宜）"
    assert suitable.pressure_display == "1.01（适宜）"

    assert high.gravity_display == "2.83（高重力，BL x1/建筑）"
    assert high.temperature_display == "96.40（高温，TSH x1/建筑）"
    assert high.pressure_display == "2.31（高压，HSE x1/建筑）"


def test_formatter_planet_resources_list_uses_type_mapping():
    from nonebot_plugin_fiqo.models import PlanetDTO, PlanetResourceDTO
    from nonebot_plugin_fiqo.utils.formatters import global_formatter

    dto = PlanetDTO(
        natural_id="VH-331a",
        name="Katoa",
        system_id="f2f57766ebaca9d69efae41ccf4d8853",
        has_rock_surface=True,
        fertility=0.5,
        gravity=1.02,
        temperature=24.0,
        pressure=1.03,
        has_adm=True,
        has_cogc=False,
        has_localmarket=True,
        has_warehouse=True,
        has_shipyard=False,
        resources=[
            PlanetResourceDTO(
                type="GASEOUS",
                factor=0.25,
                ticker="O",
                daily_extraction=15.0,
                max_extraction_in_world=43.26,
            ),
            PlanetResourceDTO(
                type="MINERAL",
                factor=0.05,
                ticker="HAL",
                daily_extraction=3.5,
                max_extraction_in_world=20.47,
            ),
        ],
    )

    result = global_formatter.format_planet_resources_list(dto)

    assert "O (气态) - 15.00/天" in result
    assert "HAL (固态) - 3.50/天" in result


def test_formatter_cx_material_keeps_order_book_formatting():
    from nonebot_plugin_fiqo.models import CXOrder, CXMaterialDTO
    from nonebot_plugin_fiqo.utils.formatters import global_formatter

    dto = CXMaterialDTO(
        ticker="RAT",
        exchange="NC1",
        currency="ICA",
        price=100.0,
        ask_price=101.0,
        ask_size=10,
        bid_price=99.0,
        bid_size=8,
        traded=200,
        supply=300,
        demand=250,
        MM_buy=None,
        MM_sell=None,
        timestamp=datetime.now(timezone.utc),
        buy_orders=[
            CXOrder(company_code="DRML", price=99.0, amount=8),
            CXOrder.model_validate(
                {"company_code": "CIMM", "price": 98.5, "amount": None}
            ),
        ],
        sell_orders=[
            CXOrder(company_code="RX7", price=101.0, amount=10),
            CXOrder(company_code="RNHT", price=102.5, amount=2),
        ],
    )

    result = global_formatter.format_cx_material(dto, 2)

    assert "卖单前2：" in result
    assert "买单前2：" in result
    assert "∞ @  98.50 ICA [CIMM]" in result
    assert "8 @  99.00 ICA [DRML]" in result
    assert "10 @ 101.00 ICA [RX7]" in result


def test_fit_service_uses_explicit_capacity(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client
    from nonebot_plugin_fiqo.models import MaterialDTO
    from nonebot_plugin_fiqo.services.fit_service import FitService

    async def mock_get_material_info(ticker: str):
        assert ticker == "AEF"
        return MaterialDTO(
            ticker="AEF",
            name="aerostatEstabilizedFoundation",
            category="Construction Materials",
            weight=5.0,
            volume=5.0,
        )

    monkeypatch.setattr(fio_client, "get_material_info", mock_get_material_info)

    result = asyncio.run(
        FitService.get_fit_info(
            ticker="AEF",
            max_weight=3000,
            max_volume=1000,
        )
    )

    assert "最大装载量：200" in result
    assert "剩余重量：2000.00 t/吨" in result
    assert "剩余体积：0.00 m³/立方米" in result
    assert "限制因素：体积受限" in result


def test_fit_service_accepts_swapped_capacity_order(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client
    from nonebot_plugin_fiqo.models import MaterialDTO
    from nonebot_plugin_fiqo.services.fit_service import FitService

    async def mock_get_material_info(ticker: str):
        assert ticker == "AEF"
        return MaterialDTO(
            ticker="AEF",
            name="aerostatEstabilizedFoundation",
            category="Construction Materials",
            weight=5.0,
            volume=5.0,
        )

    monkeypatch.setattr(fio_client, "get_material_info", mock_get_material_info)

    result = asyncio.run(
        FitService.get_fit_info(
            ticker="AEF",
            max_weight=3000,
            max_volume=1000,
        )
    )

    assert "最大装载量：200" in result


def test_fit_service_uses_configured_preset(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client
    from nonebot_plugin_fiqo.models import MaterialDTO
    from nonebot_plugin_fiqo.services.fit_service import FitService

    async def mock_get_material_info(ticker: str):
        assert ticker == "AEF"
        return MaterialDTO(
            ticker="AEF",
            name="aerostatEstabilizedFoundation",
            category="Construction Materials",
            weight=5.0,
            volume=5.0,
        )

    monkeypatch.setattr(fio_client, "get_material_info", mock_get_material_info)

    result = asyncio.run(
        FitService.get_fit_info(
            ticker="AEF",
            max_weight=3000,
            max_volume=1000,
            preset_key="WCB",
            preset_name="高负荷货舱套装",
            preset_weight=3000,
            preset_volume=1000,
        )
    )

    assert "最大装载量：200" in result
    assert "运力预设：高负荷货舱套装 (WCB) 3000t/1000m³" in result


def test_fit_service_calculates_fitratio(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client
    from nonebot_plugin_fiqo.models import MaterialDTO
    from nonebot_plugin_fiqo.services.fit_service import FitService

    async def mock_get_material_info(ticker: str):
        materials = {
            "AEF": MaterialDTO(
                ticker="AEF",
                name="aerostatEstabilizedFoundation",
                category="Construction Materials",
                weight=5.0,
                volume=5.0,
            ),
            "MCG": MaterialDTO(
                ticker="MCG",
                name="mineralConstructionGranulate",
                category="Construction Materials",
                weight=2.0,
                volume=1.0,
            ),
            "HSE": MaterialDTO(
                ticker="HSE",
                name="hardenedStructuralElements",
                category="Construction Materials",
                weight=10.0,
                volume=2.0,
            ),
        }
        return materials[ticker]

    monkeypatch.setattr(fio_client, "get_material_info", mock_get_material_info)

    result = asyncio.run(
        FitService.get_fitratio_info(
            materials=[("AEF", 2), ("MCG", 3), ("HSE", 1)],
            max_weight=100.0,
            max_volume=20.0,
            preset_key="WCB",
            preset_name="高负荷货舱套装",
            preset_weight=3000,
            preset_volume=1000,
        )
    )

    assert "最大装载组数：1" in result
    assert "剩余重量：74.00 t/吨" in result
    assert "剩余体积：5.00 m³/立方米" in result
    assert "限制因素：体积受限" in result
    assert "每组重量：26.000 t/吨" in result
    assert "每组体积：15.000 m³/立方米" in result
    assert " - 2 AEF" in result
    assert " - 3 MCG" in result
    assert " - 1 HSE" in result
    assert "运力预设：高负荷货舱套装 (WCB) 3000t/1000m³" in result


def test_uinfo_service_builds_tasks_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.services.uinfo_service import UinfoService
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_user_and_company_info(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str:
        if username == "alice":
            return "用户与公司A"
        if company_code == "ALC":
            return "用户与公司A"
        if company_name == "Alice Corp":
            return "用户与公司B"
        raise AssertionError("unexpected lookup arguments")

    monkeypatch.setattr(
        GameInfoService,
        "get_user_and_company_info",
        staticmethod(mock_get_user_and_company_info),
    )

    result = asyncio.run(
        UinfoService.get_uinfo_results(
            username="alice",
            company_code="ALC",
            company_name="Alice Corp",
        )
    )

    assert sorted(result.contents) == ["用户与公司A", "用户与公司B"]
    assert result.warnings == []


def test_verify_groupname_service_builds_report(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.models import UserAndCompanyDTO
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService
    from nonebot_plugin_fiqo.services.verify_groupname_service import (
        VerifyGroupnameService,
    )

    dto = UserAndCompanyDTO(
        user_id="user-1",
        company_id="company-1",
        username="alice",
        subscription_level="STANDARD",
        company_name="Alice Corp",
        company_code="ALC",
        rating="A",
        created_epoch_ms=0,
        faction="IC",
        bases=[],
        offices=[],
    )

    async def mock_identify_user_company_token(
        ticker: str,
        index: int,
    ) -> tuple[str, list[tuple[str, UserAndCompanyDTO | None]]]:
        if index == 0:
            return (ticker, [("派系", None)])
        return (ticker, [("用户名", dto)])

    monkeypatch.setattr(
        GameInfoService,
        "identify_user_company_token",
        staticmethod(mock_identify_user_company_token),
    )

    result = asyncio.run(VerifyGroupnameService.get_verification_report("IC丨alice"))

    assert "分隔符警告" in result
    assert "- 字段 'IC' 指向信息：派系" in result
    assert "- 字段 'alice' 指向信息：用户名" in result
    assert "用户名：alice" in result
    assert "公司代码：ALC" in result


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
async def test_planet_dto_rejects_single_non_exact_planner_result(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import planner_client
    from nonebot_plugin_fiqo.exceptions import PlanetNotFoundError
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "Katoa"
        return [
            make_planner_planet(
                natural_id="VH-331b",
                name="Katoa Prime",
            )
        ]

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
async def test_planet_dto_prefers_active_cogc_program_type_outside_local_window(
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
                active_cogc_program_type="ACTIVE_FROM_PLANNER",
                cogc_programs=[
                    CoGCProgramDTO(
                        type="ACTIVE_FROM_PLANNER",
                        start_epoch_ms=0,
                        end_epoch_ms=1,
                    ),
                    CoGCProgramDTO(
                        type="LOCAL_ACTIVE",
                        start_epoch_ms=1700000000000,
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
    assert dto.cogc_program.type == "ACTIVE_FROM_PLANNER"


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


@pytest.mark.asyncio
async def test_system_info_uses_system_dto(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client, planner_client
    from nonebot_plugin_fiqo.models import SystemDTO, CoGCProgramDTO
    from nonebot_plugin_fiqo.services.i18n_service import i18n_service
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_system_info(system_id_or_name: str):
        assert system_id_or_name == "VH-331"
        return SystemDTO(
            natural_id="VH-331",
            name="Vallis Hydri",
            meteoroid_density=0.25,
        )

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "VH-331"
        return [
            make_planner_planet(
                natural_id="VH-331a",
                name="Katoa",
                cogc_programs=[
                    CoGCProgramDTO(
                        type="ADVERTISING_AGRICULTURE",
                        start_epoch_ms=1700000000000,
                        end_epoch_ms=4102444800000,
                    )
                ],
                active_cogc_program_type="ADVERTISING_AGRICULTURE",
            ),
            make_planner_planet(
                natural_id="VH-331b",
                name="Promitor",
                cogc_programs=[],
                active_cogc_program_type=None,
            ),
            make_planner_planet(
                natural_id="VH-331",
                name="NotAPlanet",
            ),
            make_planner_planet(
                natural_id="VH-331aa",
                name="NotAPlanetEither",
            ),
            make_planner_planet(
                natural_id="ZZ-999a",
                name="OtherSystem",
            ),
        ]

    async def mock_get_cogc_program_i18n_name(program_name: str) -> str:
        assert program_name == "ADVERTISING_AGRICULTURE"
        return "农业广告"

    monkeypatch.setattr(fio_client, "get_system_info", mock_get_system_info)
    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    monkeypatch.setattr(
        i18n_service, "get_cogc_program_i18n_name", mock_get_cogc_program_i18n_name
    )

    result = await GameInfoService.get_system_info("VH-331")

    assert "编号：VH-331" in result
    assert "名称：Vallis Hydri" in result
    assert "小行星密度：0.25" in result
    assert "星球：" in result
    assert " - VH-331a Katoa - 农业广告" in result
    assert " - VH-331b Promitor - 无" in result
    assert "NotAPlanet" not in result
    assert "OtherSystem" not in result


@pytest.mark.asyncio
async def test_system_info_supports_system_name_search_for_planets(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client, planner_client
    from nonebot_plugin_fiqo.models import SystemDTO, CoGCProgramDTO
    from nonebot_plugin_fiqo.services.i18n_service import i18n_service
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_system_info(system_id_or_name: str):
        assert system_id_or_name == "Vallis Hydri"
        return SystemDTO(
            natural_id="VH-331",
            name="Vallis Hydri",
            meteoroid_density=0.25,
        )

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "VH-331"
        return [
            make_planner_planet(
                natural_id="VH-331a",
                name="Katoa",
                cogc_programs=[
                    CoGCProgramDTO(
                        type="ADVERTISING_AGRICULTURE",
                        start_epoch_ms=1700000000000,
                        end_epoch_ms=4102444800000,
                    )
                ],
                active_cogc_program_type="ADVERTISING_AGRICULTURE",
            )
        ]

    async def mock_get_cogc_program_i18n_name(program_name: str) -> str:
        return "农业广告"

    monkeypatch.setattr(fio_client, "get_system_info", mock_get_system_info)
    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)
    monkeypatch.setattr(
        i18n_service, "get_cogc_program_i18n_name", mock_get_cogc_program_i18n_name
    )

    result = await GameInfoService.get_system_info("Vallis Hydri")

    assert "编号：VH-331" in result
    assert "名称：Vallis Hydri" in result
    assert " - VH-331a Katoa - 农业广告" in result


@pytest.mark.asyncio
async def test_system_info_keeps_base_info_when_no_matching_planets(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client, planner_client
    from nonebot_plugin_fiqo.models import SystemDTO
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_system_info(system_id_or_name: str):
        assert system_id_or_name == "VH-331"
        return SystemDTO(
            natural_id="VH-331",
            name="Vallis Hydri",
            meteoroid_density=0.25,
        )

    async def mock_get_planner_planet_info(name_or_id: str):
        assert name_or_id == "VH-331"
        return [make_planner_planet(natural_id="VH-331aa", name="FilteredOut")]

    monkeypatch.setattr(fio_client, "get_system_info", mock_get_system_info)
    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)

    result = await GameInfoService.get_system_info("VH-331")

    assert "编号：VH-331" in result
    assert "名称：Vallis Hydri" in result
    assert "星球：" not in result


@pytest.mark.asyncio
async def test_system_info_keeps_base_info_when_planner_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    from nonebot_plugin_fiqo.api import fio_client, planner_client
    from nonebot_plugin_fiqo.models import SystemDTO
    from nonebot_plugin_fiqo.exceptions import BadConnectionError
    from nonebot_plugin_fiqo.services.game_info_service import GameInfoService

    async def mock_get_system_info(system_id_or_name: str):
        assert system_id_or_name == "VH-331"
        return SystemDTO(
            natural_id="VH-331",
            name="Vallis Hydri",
            meteoroid_density=0.25,
        )

    async def mock_get_planner_planet_info(name_or_id: str):
        raise BadConnectionError("planner unavailable")

    monkeypatch.setattr(fio_client, "get_system_info", mock_get_system_info)
    monkeypatch.setattr(planner_client, "get_planet_info", mock_get_planner_planet_info)

    result = await GameInfoService.get_system_info("VH-331")

    assert "编号：VH-331" in result
    assert "名称：Vallis Hydri" in result
    assert "星球：" not in result


def test_formatter_system_planet_list_omits_duplicate_name():
    from nonebot_plugin_fiqo.models import SystemPlanetSummaryDTO
    from nonebot_plugin_fiqo.utils.formatters import global_formatter

    result = global_formatter.format_system_planet_list(
        [
            SystemPlanetSummaryDTO(
                natural_id="VH-331a",
                name="Katoa",
                cogc_type="农业广告",
            ),
            SystemPlanetSummaryDTO(
                natural_id="VH-331b",
                name=None,
                cogc_type=None,
            ),
            SystemPlanetSummaryDTO(
                natural_id="VH-331c",
                name="VH-331c",
                cogc_type="无",
            ),
        ]
    )

    assert " - VH-331a Katoa - 农业广告" in result
    assert " - VH-331b - 无" in result
    assert " - VH-331c - 无" in result
