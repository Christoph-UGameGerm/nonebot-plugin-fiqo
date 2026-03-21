from typing import Any

import httpx
from nonebot import get_driver, logger
from pydantic import BaseModel, SecretStr

from nonebot_plugin_fiqo.api import BaseClient
from nonebot_plugin_fiqo.config import (
    WeblateConfig,
    plugin_config,
)
from nonebot_plugin_fiqo.exceptions import (
    I18nNotFoundError,
)
from nonebot_plugin_fiqo.models import I18nDictDTO


class WeblateEndpoint(BaseModel):
    base_url: str = "https://weblate.simulogics.games/api"
    project: str = "simulogics-games"
    component: str = "prosperous-universe-frontend"
    language_code: str = "zh_Hans"

    @property
    def units(self) -> str:
        return (
            f"/translations/{self.project}/{self.component}/{self.language_code}/units/"
        )


class WeblateAuth(httpx.Auth):
    def __init__(self, api_token: SecretStr) -> None:
        self.api_token = api_token

    def auth_flow(self, request: httpx.Request) -> Any:
        request.headers["Authorization"] = f"Token {self.api_token.get_secret_value()}"
        yield request


ENDPOINTS = WeblateEndpoint()


class WeblateClient(BaseClient):
    def __init__(self, config: WeblateConfig) -> None:
        super().__init__(base_url=ENDPOINTS.base_url, timeout=10)
        if config.api_token:
            self.client.auth = WeblateAuth(config.api_token)
        self.client.headers.update({"User-Agent": "CommunityBot/WeblateClient"})

    async def get_units(self, query: str, cache_key: str) -> I18nDictDTO:
        return await self.request(
            key_and_model=(cache_key, I18nDictDTO),
            endpoint=ENDPOINTS.units,
            params={"q": query},
            not_found_error=I18nNotFoundError(query=query),
            ttl=None,
        )


weblate_client = WeblateClient(config=plugin_config.weblate)


@get_driver().on_shutdown
async def shutdown_weblate_client() -> None:
    await weblate_client.close()
