from typing import TypeVar

from nonebot import logger
from pydantic import ValidationError

from . import model
from .cache_manager import cache_manager
from .exception import I18nFetchError
from .weblate_client import weblate_service


# Weblate Term Provider Implementation
class WeblateTermProvider:

    T = TypeVar("T", bound=model.BaseModel)

    async def _generic_get(self, query: str, model_cls: type[T], entity_id: str) -> T:
        """
        Intenal method to perform a get request to Cache and/or Weblate\
            with privided query string and model class for validation and parsing.

        :param query: Query string to search for translation units on Weblate
        :type query: str
        :param model_cls: Pydantic model class to validate\
            and parse the Weblate response into
        :type model_cls: T
        :return: Parsed model instance containing the requested information
        :rtype: T
        :raises I18nFetchError: If an error occurs while fetching\
            or parsing the information
        :raises BadConnectionError: If a network error occurs during the request
        """
        logger.info(f"WeblateTermProvider: Fetching information for query '{query}'\
                     with model '{model_cls.__name__}'")
        if cache_entry := cache_manager.get(model_cls, entity_id):
            logger.info(f"Cache hit for query '{query}'"
                        f"and model '{model_cls.__name__}'")
            return cache_entry
        logger.info(f"Cache miss for query '{query}' and model '{model_cls.__name__}',\
                     fetching from Weblate")
        response = await weblate_service.get_units_by_query_string(query)
        logger.debug(f"Weblate response for query '{query}': {response}")
        try:
            parsed_response = model_cls.model_validate(response)
        except ValidationError as e:
            logger.error(f"Validation error while parsing Weblate response for query\
                         '{query}' and model '{model_cls.__name__}': {e}")
            raise I18nFetchError(
                entity_id,
                f"Invalid data for model {model_cls.__name__}"
            ) from e
        cache_manager.set(parsed_response, entity_id)
        return parsed_response

    async def _get_material(self, name: str) -> model.I18nMaterial:
        """
        Internal method to fetch I18n material information from Weblate.

        :param name: Original material name from FIO API
        :type name: str
        :return: I18n material information model
        :rtype: model.I18nMaterial
        :raises I18nFetchError: If an error occurs while fetching the material
        :raises BadConnectionError: If a network error occurs during the request
        """
        query = f"key:Material.{name}"
        return await self._generic_get(query, model.I18nMaterial, name)

    async def _get_building(self, name: str) -> model.I18nBuilding:
        """
        Internal method to fetch I18n building information from Weblate.

        :param name: Original building name from FIO API
        :type name: str
        :return: I18n building information model
        :rtype: model.I18nBuilding
        :raises I18nFetchError: If an error occurs while fetching the building
        :raises BadConnectionError: If a network error occurs during the request
        """
        query = f"key:Reactor.{name}_"
        return await self._generic_get(query, model.I18nBuilding, name)

    async def get_material_name(self, name: str) -> str:
        """
        Get localized material name by FIO name.

        :param name: Original material name from FIO API
        :type name: str
        :return: Localized material name
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the name
        :raises BadConnectionError: If a network error occurs during the request
        """
        i18n_material = await self._get_material(name)
        return i18n_material.get_field(name, "name")

    async def get_material_description(self, name: str) -> str:
        """
        Get localized material description by FIO name.

        :param name: Original material name from FIO API
        :type name: str
        :return: Localized material description
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the description
        :raises BadConnectionError: If a network error occurs during the request
        """
        i18n_material = await self._get_material(name)
        return i18n_material.get_field(name, "description")

    async def get_material_category(self, name: str) -> str:
        """
        Get localized material category name by original category name.

        :param name: Original material category name from FIO API
        :type name: str
        :return: Localized material category name
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the category name
        :raises BadConnectionError: If a network error occurs during the request
        """
        query = "key:MaterialCategory."
        i18n_categories = await self._generic_get(query, model.I18nCategories, name)
        return i18n_categories.get_category_name(name)

    async def get_building_name(self, name: str) -> str:
        """
        Get localized building name by FIO name.

        :param name: Original building name from FIO API
        :type name: str
        :return: Localized building name
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the name
        :raises BadConnectionError: If a network error occurs during the request
        """
        i18n_building = await self._get_building(name)
        return i18n_building.get_field(name, "name")

    async def get_building_description(self, name: str) -> str:
        """
        Get localized building description by FIO name.

        :param name: Original building name from FIO API
        :type name: str
        :return: Localized building description
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the description
        :raises BadConnectionError: If a network error occurs during the request
        """
        i18n_building = await self._get_building(name)
        return i18n_building.get_field(name, "description")

    async def get_expertise(self, name: str) -> str:
        """
        Get localized expertise name by FIO name.

        :param name: Original expertise name from FIO API
        :type name: str
        :return: Localized expertise name
        :rtype: str
        """
        query = f"ExpertiseCategory.{name}"
        i18n_expertise = await self._generic_get(query, model.I18nExpertise, name)
        return i18n_expertise.get_expertise_name(name)

weblate_provider = WeblateTermProvider()
