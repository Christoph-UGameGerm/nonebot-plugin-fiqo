from nonebot import logger

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.api import fio_client
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.models import (
    BuildingDTO,
    CXMaterialDTO,
    MaterialDTO,
    RecipeDTO,
)
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.utils.formatters import (
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
    async def get_material_info(ticker: str) -> str:
        fio_response = await fio_client.get_material_info(ticker)
        info = MaterialDTO.from_fio_response(fio_response)
        logger.info(f"Fetched material info for {ticker=}: {fio_response=}")
        info.name = await i18n_service.get_material_i18n_name(fio_response.name)
        info.category = await i18n_service.get_material_i18n_category(
            fio_response.category
        )
        info.desc = await i18n_service.get_material_i18n_desc(fio_response.name)
        return global_formatter.format_material(info)

    @staticmethod
    async def get_material_info_with_recipes(ticker: str) -> str:
        material_response = await FIOService.get_material_info(ticker)
        recipe_response = await FIOService.get_recipe_info(ticker)
        return material_response + "\n" + recipe_response

    @staticmethod
    async def get_building_info(ticker: str) -> str:
        fio_response = await fio_client.get_building_info(ticker)
        info = BuildingDTO.from_fio_response(fio_response)
        logger.info(f"Fetched building info for {ticker=}: {fio_response=}")
        info.name = await i18n_service.get_building_i18n_name(fio_response.name)
        info.desc = await i18n_service.get_building_i18n_desc(fio_response.name)
        info.expertise = await i18n_service.get_expertise_name(fio_response.expertise)
        return global_formatter.format_building(info)

    @staticmethod
    async def get_exchange_material_info(ticker: str, order_no: int) -> str:
        fio_response = await fio_client.get_cx_material_info(ticker)
        info = CXMaterialDTO.from_fio_response(fio_response)
        return global_formatter.format_cx_material(info, order_no)

fio_service = FIOService()
