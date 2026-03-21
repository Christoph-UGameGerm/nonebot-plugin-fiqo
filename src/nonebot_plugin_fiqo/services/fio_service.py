import asyncio
from typing import Literal

from nonebot import logger
from pydantic import BaseModel

from nonebot_plugin_fiqo.api import fio_client
from nonebot_plugin_fiqo.config import plugin_config
from nonebot_plugin_fiqo.exceptions import (
    WrongUsernameOrCompanyTickerError,
)
from nonebot_plugin_fiqo.models import (
    BuildingDTO,
    CXMaterialDTO,
    MaterialDTO,
    RecipeDTO,
    UserAndCompanyDTO,
)
from nonebot_plugin_fiqo.utils import (
    global_formatter,
)

from .i18n_service import i18n_service


class FIOService:
    @staticmethod
    async def get_recipe_info(ticker: str) -> str:
        fio_response = await fio_client.get_recipe_info(ticker)
        logger.info(f"Fetched recipe info for {ticker=}: {fio_response=}")
        from_recipes = [
            RecipeDTO.from_fio_response(r)
            for r in fio_response.root
            if r.outputs and any(o.ticker == ticker for o in r.outputs)
        ]
        to_recipes = [
            RecipeDTO.from_fio_response(r)
            for r in fio_response.root
            if r.inputs and any(i.ticker == ticker for i in r.inputs)
        ]
        from_recipes_reponse = global_formatter.format_recipe_list(from_recipes)
        to_recipes_response = global_formatter.format_recipe_list(to_recipes)
        lines = [
            f"生产：\n{from_recipes_reponse}" if from_recipes else "",
            f"产品：\n{to_recipes_response}" if to_recipes else "",
        ]
        return "\n".join([line for line in lines if line])

    @staticmethod
    async def get_material_dto(ticker: str) -> MaterialDTO:
        fio_response = await fio_client.get_material_info(ticker)
        info = MaterialDTO.from_fio_response(fio_response)
        info.name = await i18n_service.get_material_i18n_name(fio_response.name)
        info.category = await i18n_service.get_material_i18n_category(
            fio_response.category
        )
        info.desc = await i18n_service.get_material_i18n_desc(fio_response.name)
        return info

    @staticmethod
    async def get_material_info(ticker: str) -> str:
        dto = await FIOService.get_material_dto(ticker)
        return global_formatter.format_material(dto)

    @staticmethod
    async def get_material_info_with_recipes(ticker: str) -> str:
        material_response = await FIOService.get_material_info(ticker)
        recipe_response = await FIOService.get_recipe_info(ticker)
        return material_response + "\n" + recipe_response

    @staticmethod
    async def get_building_dto(ticker: str) -> BuildingDTO:
        fio_response = await fio_client.get_building_info(ticker)
        info = BuildingDTO.from_fio_response(fio_response)
        info.name = await i18n_service.get_building_i18n_name(fio_response.name)
        info.desc = await i18n_service.get_building_i18n_desc(fio_response.name)
        info.expertise = await i18n_service.get_expertise_name(fio_response.expertise)
        return info

    @staticmethod
    async def get_building_info(ticker: str) -> str:
        dto = await FIOService.get_building_dto(ticker)
        return global_formatter.format_building(dto)

    @staticmethod
    async def get_exchange_material_dto(ticker: str) -> CXMaterialDTO:
        fio_response = await fio_client.get_cx_material_info(ticker)
        return CXMaterialDTO.from_fio_response(fio_response)

    @staticmethod
    async def get_exchange_material_info(ticker: str, order_no: int) -> str:
        dto = await FIOService.get_exchange_material_dto(ticker)
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
        return UserAndCompanyDTO.from_fio_response(fio_response)

    @staticmethod
    async def get_user_and_company_info(
        username: str | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> str:
        info = await FIOService.get_user_and_company_dto(
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
            FIOService.get_user_and_company_dto(username=ticker),
            FIOService.get_user_and_company_dto(company_code=ticker_upper),
            FIOService.get_user_and_company_dto(company_name=ticker),
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


fio_service = FIOService()
