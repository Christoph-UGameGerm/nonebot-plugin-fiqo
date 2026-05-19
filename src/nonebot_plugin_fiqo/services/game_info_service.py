import asyncio

from nonebot import logger
from pydantic import ValidationError

from nonebot_plugin_fiqo.api import fio_client, planner_client
from nonebot_plugin_fiqo.utils import global_formatter
from nonebot_plugin_fiqo.config import plugin_config
from nonebot_plugin_fiqo.models import (
    PlanetDTO,
    BuildingDTO,
    MaterialDTO,
    CXMaterialDTO,
    UserAndCompanyDTO,
)
from nonebot_plugin_fiqo.exceptions import (
    I18nFetchError,
    BadConnectionError,
    PlanetNotFoundError,
    WrongSystemTickerError,
    WrongUsernameOrCompanyTickerError,
)

from .i18n_service import i18n_service


class GameInfoService:
    @staticmethod
    async def get_recipe_info(ticker: str) -> str:
        recipe_info_list = await fio_client.get_recipe_info(ticker)
        logger.info(f"Fetched recipe info for {ticker=}: {recipe_info_list=}")
        from_recipes = [
            r
            for r in recipe_info_list
            if r.outputs and any(o.ticker == ticker for o in r.outputs)
        ]
        to_recipes = [
            r
            for r in recipe_info_list
            if r.inputs and any(i.ticker == ticker for i in r.inputs)
        ]
        from_recipes_response = global_formatter.format_recipe_list(from_recipes)
        to_recipes_response = global_formatter.format_recipe_list(to_recipes)
        lines = [
            f"生产：\n{from_recipes_response}" if from_recipes else "",
            f"产品：\n{to_recipes_response}" if to_recipes else "",
        ]
        return "\n".join([line for line in lines if line])

    @staticmethod
    async def get_material_dto(ticker: str) -> MaterialDTO:
        info = await fio_client.get_material_info(ticker)
        name_task = i18n_service.get_material_i18n_name(info.name)
        category_task = i18n_service.get_material_i18n_category(info.category)
        desc_task = i18n_service.get_material_i18n_desc(info.name)

        info.name, info.category, info.desc = await asyncio.gather(
            name_task, category_task, desc_task
        )
        return info

    @staticmethod
    async def get_material_info(ticker: str) -> str:
        dto = await GameInfoService.get_material_dto(ticker)
        return global_formatter.format_material(dto)

    @staticmethod
    async def get_material_info_with_recipes(ticker: str) -> str:
        material_response = await GameInfoService.get_material_info(ticker)
        recipe_response = await GameInfoService.get_recipe_info(ticker)
        return material_response + "\n" + recipe_response

    @staticmethod
    async def get_building_dto(ticker: str) -> BuildingDTO:
        info = await fio_client.get_building_info(ticker)

        name_task = i18n_service.get_building_i18n_name(info.name)
        desc_task = i18n_service.get_building_i18n_desc(info.name)
        expertise_task = i18n_service.get_expertise_name(info.expertise)

        info.name, info.desc, info.expertise = await asyncio.gather(
            name_task, desc_task, expertise_task
        )
        return info

    @staticmethod
    async def get_building_info(ticker: str) -> str:
        dto = await GameInfoService.get_building_dto(ticker)
        return global_formatter.format_building(dto)

    @staticmethod
    async def get_exchange_material_dto(ticker: str) -> CXMaterialDTO:
        return await fio_client.get_cx_material_info(ticker)

    @staticmethod
    async def get_exchange_material_info(ticker: str, order_no: int) -> str:
        dto = await GameInfoService.get_exchange_material_dto(ticker)
        return global_formatter.format_cx_material(dto, order_no)

    @staticmethod
    async def get_user_and_company_dto(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> UserAndCompanyDTO:
        if username:
            fio_response = await fio_client.get_user_and_company_info(username=username)
        elif company_code:
            fio_response = await fio_client.get_user_and_company_info(
                company_code=company_code
            )
        elif company_name:
            fio_response = await fio_client.get_user_and_company_info(
                company_name=company_name
            )
        else:
            raise WrongUsernameOrCompanyTickerError("未知")
        return fio_response

    @staticmethod
    async def get_user_and_company_info(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str:
        info = await GameInfoService.get_user_and_company_dto(
            username=username, company_code=company_code, company_name=company_name
        )
        return global_formatter.format_user_company_info(info)

    @staticmethod
    async def identify_user_company_token(
        ticker: str,
        index: int,
    ) -> tuple[str, list[tuple[str, UserAndCompanyDTO | None]]]:
        ticker_upper = ticker.upper()
        if index == 0 and ticker_upper in plugin_config.game.all_ingame_fas:
            return (ticker, [("派系", None)])

        matches = []

        tasks = [
            GameInfoService.get_user_and_company_dto(username=ticker),
            GameInfoService.get_user_and_company_dto(company_code=ticker_upper),
            GameInfoService.get_user_and_company_dto(company_name=ticker),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        username_res, company_code_res, company_name_res = results
        if not isinstance(username_res, Exception) and username_res is not None:
            matches.append(("用户名", username_res))
        if not isinstance(company_code_res, Exception) and company_code_res is not None:
            matches.append(("公司代码", company_code_res))
        if not isinstance(company_name_res, Exception) and company_name_res is not None:
            matches.append(("公司名称", company_name_res))

        if not matches:
            matches.append(("未知", None))

        return (ticker, matches)

    @staticmethod
    async def get_planet_dto(name_or_id: str) -> PlanetDTO:
        try:
            planner_planets = await planner_client.get_planet_info(name_or_id)
        except (BadConnectionError, PlanetNotFoundError, ValidationError) as e:
            logger.warning(f"Planner planet data unavailable for {name_or_id=}: {e}")
            raise

        query_normalized = name_or_id.casefold()
        planner_info = next(
            (
                planet
                for planet in planner_planets
                if planet.natural_id.casefold() == query_normalized
                or (
                    planet.name is not None
                    and planet.name.casefold() == query_normalized
                )
            ),
            None,
        )
        if planner_info is None:
            raise PlanetNotFoundError(name_or_id)

        data = PlanetDTO.from_planner(planner_info)
        try:
            system_info = await fio_client.get_system_info(data.system_id)
        except (BadConnectionError, ValidationError, WrongSystemTickerError) as e:
            logger.warning(f"System data unavailable for {data.system_id=}: {e}")
        else:
            data.system_name = system_info.name
            data.system_natural_id = system_info.natural_id

        if data.cogc_status is not None:
            try:
                data.cogc_status = await i18n_service.get_cogc_i18n_status(
                    data.cogc_status
                )
            except I18nFetchError as e:
                logger.warning(f"CoGC status i18n unavailable: {e}")

        if data.cogc_program is not None and data.cogc_program.type is not None:
            try:
                data.cogc_program.type = await i18n_service.get_cogc_program_i18n_name(
                    data.cogc_program.type
                )
            except I18nFetchError as e:
                logger.warning(f"CoGC program i18n unavailable: {e}")
        return data

    @staticmethod
    async def get_planet_info(name_or_id: str) -> str:
        info = await GameInfoService.get_planet_dto(name_or_id)
        return global_formatter.format_planet(info)


info_service = GameInfoService()
