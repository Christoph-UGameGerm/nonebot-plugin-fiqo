from nonebot import logger

from . import model
from .cache_manager import cache_manager
from .weblate_client import weblate_service


# Weblate Term Provider Implementation
class WeblateTermProvider:

    async def get_material_name(self, ticker: str, name: str) -> str:
        """
        Get localized material name by ticker and FIO name.

        :param ticker: Material ticker code
        :type ticker: str
        :param name: Original material name from FIO API
        :type name: str
        :return: Localized material name
        :rtype: str
        """
        logger.info(f"WeblateTermProvider:"
                    f"Fetching material name for ticker '{ticker}'")
        if cache_entry := cache_manager.get(model.I18nMaterial, ticker):
            logger.info(f"Cache hit for material '{ticker}'")
            return cache_entry.get_field(name, "name")
        logger.info(f"Cache miss for material '{ticker}', fetching from Weblate")
        query = f"key:Material.{name}"
        response = await weblate_service.get_units_by_query_string(query)
        logger.debug(f"Weblate response for material name query '{query}': {response}")
        i18n_material = model.I18nMaterial.model_validate(response)
        cache_manager.set(i18n_material, ticker)
        return i18n_material.get_field(name, "name")

    async def get_material_description(self, ticker: str, name: str) -> str:
        """
        Get localized material description by ticker and FIO name.

        :param ticker: Material ticker code
        :type ticker: str
        :param name: Original material name from FIO API
        :type name: str
        :return: Localized material description
        :rtype: str
        """
        logger.info(f"WeblateTermProvider:"
                    f"Fetching material description for ticker '{ticker}'")
        if cache_entry := cache_manager.get(model.I18nMaterial, ticker):
            logger.info(f"Cache hit for material '{ticker}'")
            return cache_entry.get_field(name, "description")
        logger.info(f"Cache miss for material '{ticker}', fetching from Weblate")
        query = f"key:Material.{name}"
        response = await weblate_service.get_units_by_query_string(query)
        logger.debug(f"Weblate response for material description query '{query}':"
                     f"{response}")
        i18n_material = model.I18nMaterial.model_validate(response)
        cache_manager.set(i18n_material, ticker)
        return i18n_material.get_field(name, "description")

    async def get_material_category(self, name: str) -> str:
        """
        Get localized material category name by original category name.

        :param name: Original material category name from FIO API
        :type name: str
        :return: Localized material category name
        :rtype: str
        """
        logger.info(f"WeblateTermProvider:"
                    f"Fetching material category name for category '{name}'")
        cache_entry = cache_manager.get(model.I18nCategories, "categories")
        if cache_entry and (i18n_name := cache_entry.get_category_name(name)):
            logger.info(f"Cache hit for material category '{name}'")
            return i18n_name
        logger.info(f"Cache miss for material category '{name}', fetching from Weblate")
        query = "key:MaterialCategory."
        response = await weblate_service.get_units_by_query_string(query)
        logger.debug(f"Weblate response for material category '{query}': {response}")
        i18n_categories = model.I18nCategories.model_validate(response)
        cache_manager.set(i18n_categories, "categories")
        return i18n_categories.get_category_name(name)

    async def get_building_name(self, name: str) -> str:
        # Implementation to fetch localized building name from Weblate
        return ""

    async def get_building_expertise(self, name: str) -> str:
        # Implementation to fetch localized building expertise from Weblate
        return ""

weblate_provider = WeblateTermProvider()
