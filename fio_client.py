from typing import Any, Optional

import httpx
from nonebot import get_driver, logger
from pydantic import BaseModel, TypeAdapter, ValidationError

from . import exception, model


class FioEndpoint(BaseModel):
    base_url: str = "https://api.fnar.net"
    material: str = "/material"

ENDPOINTS = FioEndpoint()

class FioClient:
    _client: Optional[httpx.AsyncClient] = None

    def __init__(self) -> None:
        self.base_url = ENDPOINTS.base_url
        self.timeout = 10.

    async def get_client(self) -> httpx.AsyncClient:
        """
        Get the global HTTPX AsyncClient for Fio API requests.

        :return: The global HTTPX AsyncClient instance
        :rtype: AsyncClient
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "CommunityBot/FioClient"
                }
            )
        return self._client

    async def close(self) -> None:
        """
        Close the global HTTPX AsyncClient if it exists.
        """
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """
        Encapsulated method to perform requests to the FIO API with provided endpoint\
            and parameters.

        :param endpoint: The API endpoint to request
        :type endpoint: str
        :param params: HTTP Request parameters for the request
        :type params: Optional[dict]
        :return: The JSON response from the API
        :rtype: Any
        """
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

    async def get_material_info(self, material_tickers: list[str])\
        -> list[model.FIOMaterialResponse]:
        """
        Get material information from FIO API for the given list of material tickers.

        :param material_tickers: List of material tickers to fetch information for
        :type material_tickers: list[str]
        :return: List of response models containing material information
        :rtype: list[model.FIOMaterialResponse]
        """
        logger.debug(f"Fetching material info for tickers: {material_tickers}")
        endpoint = ENDPOINTS.material
        params = {
            "ticker": material_tickers
        }
        response = await self._request(endpoint, params=params)
        try:
            adapter = TypeAdapter(list[model.FIOMaterialResponse])
            return adapter.validate_python(response)
        except Exception as e:
            logger.error(f"Error validating material info response: {e}")
            if isinstance(e, ValidationError):
                raise exception.WrongMaterialTickerError(
                    material_tickers
                ) from e
            raise

    async def get_material_categories(self) -> model.FIOCategoriesResponse:
        """
        Get material categories from FIO API.

        :return: The response model containing material categories information
        :rtype: model.FIOCategoriesResponse
        """
        logger.debug("Fetching material categories")
        endpoint = "/material/categories"
        try:
            response = await self._request(endpoint)
            return model.FIOCategoriesResponse(response)
        except Exception as e:
            logger.error(f"Error fetching material categories: {e}")
            raise


fio_service = FioClient()

driver = get_driver()
@driver.on_shutdown
async def stop_fio_service() -> None:
    await fio_service.close()
