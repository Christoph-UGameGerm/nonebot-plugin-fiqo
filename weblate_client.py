from typing import Annotated, Any, Optional

import httpx
from nonebot import get_driver, get_plugin_config, logger
from pydantic import BaseModel, BeforeValidator, SecretStr, TypeAdapter

from . import exception, model
from .config import Config

plugin_config = get_plugin_config(Config).fiqo

# Weblate API Endpoints
class WeblateEndpoint(BaseModel):
    base_url: str = "https://weblate.simulogics.games/api"
    project: str = "simulogics-games"
    component: str = "prosperous-universe-frontend"
    language_code: str = "zh_Hans"
    units: str = f"/translations/{project}/{component}/{language_code}/units/"

ENDPOINTS = WeblateEndpoint()

# Authentication process for Weblate API
class WeblateAuth(httpx.Auth):
    def __init__(self, api_token: SecretStr) -> None:
        self.api_token = api_token

    def auth_flow(self, request: httpx.Request) -> Any:
        request.headers["Authorization"] = f"Token {self.api_token.get_secret_value()}"
        yield request

# Extract results from Weblate API units response
def extract_results(data: Any) -> Any:
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data

extract_results_adapter = TypeAdapter(
    Annotated[list[model.WeblateI18nUnit], BeforeValidator(extract_results)]
)

# Weblate Client Service
class WeblateClient:
    weblate_client: Optional[httpx.AsyncClient] = None

    def __init__(self,
                 api_token: SecretStr,
                 base_url: str = ENDPOINTS.base_url,
                 project_url_slug: str = ENDPOINTS.project,
                 component_url_slug: str = ENDPOINTS.component,
                 language_code: str = ENDPOINTS.language_code,
                ) -> None:
        self.api_token = api_token
        self.base_url = base_url
        self.timeout = 10.
        self.project_url_slug = project_url_slug
        self.component_url_slug = component_url_slug
        self.language_code = language_code

    async def close(self) -> None:
        """
        Close the Weblate API client if it exists.
        """
        if self.weblate_client:
            await self.weblate_client.aclose()
            self.weblate_client = None

    async def get_client(self) -> httpx.AsyncClient:
        if self.weblate_client is None:
            self.weblate_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "CommunityBot/WeblateClient",
                },
                auth=WeblateAuth(self.api_token)
            )
        return self.weblate_client

    async def _request(self, endpoint: str, params: Optional[dict] = None) -> Any:
        client = await self.get_client()
        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Response status error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise

    async def get_units_by_query_string(self, query: str)\
        -> list[model.WeblateI18nUnit]:
        logger.debug(f"Fetching Weblate translation units for query: {query}")
        endpoint = ENDPOINTS.units
        params = {
            "q": query,
        }
        try:
            response = await self._request(endpoint, params=params)
            response = extract_results_adapter.validate_python(response)
        except Exception as e:
            logger.error(f"Error fetching Weblate units for query '{query}': {e}")
            raise exception.I18nFetchError(
                query,
                str(e)
            ) from e
        return response


weblate_service = WeblateClient(
    api_token=plugin_config.weblate_api_token,
    base_url=ENDPOINTS.base_url,
    project_url_slug=ENDPOINTS.project,
    component_url_slug=ENDPOINTS.component,
    language_code=ENDPOINTS.language_code,
)

driver = get_driver()
@driver.on_shutdown
async def stop_weblate_service() -> None:
    await weblate_service.close()
