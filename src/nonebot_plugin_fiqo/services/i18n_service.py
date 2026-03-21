from nonebot_plugin_fiqo.api import weblate_client
from nonebot_plugin_fiqo.exceptions import (
    I18nFetchError,
)
from nonebot_plugin_fiqo.config import plugin_config


class I18nService:

    @property
    def _weblate_authorized(self) -> bool:
        return bool(plugin_config.weblate.api_token)

    async def get_material_field(self, name: str, field: str) -> str:
        query = f"key:Material.{name}"
        cache_key = f"wl:mat:{name}"
        exact_key = f"Material.{name}.{field}"

        i18n_dict = await weblate_client.get_units(query=query, cache_key=cache_key)
        result = i18n_dict.translations.get(exact_key)
        if not result:
            raise I18nFetchError(f"材料{name}字段{field}未找到")
        return result

    async def get_building_field(self, name: str, field: str) -> str:
        query = f"key:Reactor.{name}_{field}"
        cache_key = f"wl:bui:{name}"
        exact_key = f"Reactor.{name}_{field}"

        i18n_dict = await weblate_client.get_units(query=query, cache_key=cache_key)
        result = i18n_dict.translations.get(exact_key)
        if not result:
            raise I18nFetchError(f"建筑{name}字段{field}未找到")
        return result

    async def get_category_name(self, original_name: str) -> str:
        query = "key:MaterialCategory"
        cache_key = "wl:mat_cat"
        formatted_name = "".join(original_name.split())
        exact_key = f"MaterialCategory.{formatted_name}"

        i18n_dict = await weblate_client.get_units(query=query, cache_key=cache_key)
        result = i18n_dict.translations.get(exact_key)
        if not result:
            raise I18nFetchError(f"材料类别{original_name}未找到")
        return result

    async def get_expertise_name(self, expertise: str | None) -> str | None:
        if not expertise:
            return None
        if not self._weblate_authorized:
            return expertise + "（需配置Weblate API Token以获取中文专精）"
        query = "key:ExpertiseCategory."
        cache_key = "wl:expertise_cat"
        formatted_expertise = expertise.upper()
        exact_key = f"ExpertiseCategory.{formatted_expertise}"

        i18n_dict = await weblate_client.get_units(query=query, cache_key=cache_key)
        result = i18n_dict.translations.get(exact_key)
        if not result:
            raise I18nFetchError(f"专精类别{expertise}未找到")
        return result

    async def get_material_i18n_name(self, material_name: str) -> str:
        if not self._weblate_authorized:
            return material_name + "（需配置Weblate API Token以获取中文名称）"
        i18n_name = await self.get_material_field(material_name, "name")
        return i18n_name if i18n_name else material_name

    async def get_material_i18n_desc(self, material_name: str) -> str:
        if not self._weblate_authorized:
            return "需配置Weblate API Token以获取描述"
        i18n_desc = await self.get_material_field(material_name, "description")
        return i18n_desc if i18n_desc else ""

    async def get_material_i18n_category(self, category: str) -> str:
        if not self._weblate_authorized:
            return category + "（需配置Weblate API Token以获取中文类别）"
        i18n_category = await self.get_category_name(category)
        return i18n_category if i18n_category else category

    async def get_building_i18n_name(self, building_name: str) -> str:
        if not self._weblate_authorized:
            return building_name + "（需配置Weblate API Token以获取中文名称）"
        i18n_name = await self.get_building_field(building_name, "name")
        return i18n_name if i18n_name else building_name

    async def get_building_i18n_desc(self, building_name: str) -> str:
        if not self._weblate_authorized:
            return "需配置Weblate API Token以获取描述"
        i18n_desc = await self.get_building_field(building_name, "description")
        return i18n_desc if i18n_desc else ""


i18n_service = I18nService()
