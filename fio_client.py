from json import JSONDecodeError
from typing import Any

import httpx
from nonebot import get_driver, logger
from pydantic import BaseModel, TypeAdapter, ValidationError

from . import exception, model


class FioEndpoint(BaseModel):
    base_url: str = "https://api.fnar.net"
    material: str = "/material"
    categories: str = "/material/categories"
    building: str = "/building/"

ENDPOINTS = FioEndpoint()

class FioClient:
    _client: httpx.AsyncClient | None = None

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

    async def _request(self, endpoint: str, params: dict | None = None) -> Any:
        """
        Encapsulated method to perform requests to the FIO API with provided endpoint\
            and parameters.

        :param endpoint: The API endpoint to request
        :type endpoint: str
        :param params: HTTP Request parameters for the request
        :type params: dict | None
        :return: The JSON response from the API
        :rtype: Any
        :raises HTTPStatusError: If the response status code indicates an error
        :raises BadConnectionError: If a network error occurs during the request
        :raises JSONDecodeError: If the response body cannot be decoded as JSON
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
            raise exception.BadConnectionError(str(e)) from e
        except JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise

    async def get_material_info(self, material_ticker: str)\
        -> model.FIOMaterialResponse:
        """
        Get material information from FIO API for the given list of material tickers.

        :param material_ticker: List of material tickers to fetch information for
        :type material_ticker: list[str]
        :return: List of response models containing material information
        :rtype: list[model.FIOMaterialResponse]
        :raises WrongMaterialTickerError: If the API response contains implies\
            wrong material tickers
        :raises BadConnectionError: If a network error occurs during the request
        """
        logger.debug(f"Fetching material info for tickers: {material_ticker}")
        endpoint = ENDPOINTS.material
        params = {
            "ticker": material_ticker
        }
        try:
            response = await self._request(endpoint, params=params)
            # The response is in a list, use a type adapter to validate it
            adapter = TypeAdapter(list[model.FIOMaterialResponse])
            # Extract the final response element out of the list
            response = adapter.validate_python(response).pop()
        except (
            ValidationError,
            IndexError,
            httpx.HTTPStatusError,
            JSONDecodeError
        ) as e:
            logger.error(f"Error fetching material info: {e}")
            raise exception.WrongMaterialTickerError(material_ticker) from e
        return response

    async def get_material_categories(self) -> model.FIOCategoriesResponse:
        """
        Get material categories from FIO API.

        :return: The response model containing material categories information
        :rtype: model.FIOCategoriesResponse
        :raises CategoryNotFoundError: If the API response is not as expected
        :raises BadConnectionError: If a network error occurs during the request
        """
        logger.debug("Fetching material categories")
        endpoint = ENDPOINTS.categories
        try:
            response = await self._request(endpoint)
            response = model.FIOCategoriesResponse.model_validate(response)
        except (
            ValidationError,
            httpx.HTTPStatusError,
            JSONDecodeError
        ) as e:
            logger.error(f"Error fetching material categories: {e}")
            raise exception.CategoryNotFoundError from e
        return response

    async def get_building_info(self, building_ticker: str)\
        -> model.FIOBuildingResponse:
        """
        Get building information from FIO API for the given list of building tickers.

        :param building_ticker: List of building tickers to fetch information for
        :type building_ticker: str
        :return: The response model containing building information
        :rtype: model.FIOBuildingResponse
        :raises WrongBuildingTickerError: If the API response contains implies\
            wrong building tickers
        :raises BadConnectionError: If a network error occurs during the request
        """
        params = {
            "include_costs": True,
            "include_recipes": True
        }
        logger.info(f"Fetching building info for ticker: {building_ticker}")
        endpoint = ENDPOINTS.building + building_ticker
        try:
            response = await self._request(endpoint, params=params)
            response = model.FIOBuildingResponse.model_validate(response)
        except (
            ValidationError,
            httpx.HTTPStatusError,
            JSONDecodeError
        ) as e:
            logger.error(f"Error fetching building info: {e}")
            raise exception.WrongBuildingTickerError(building_ticker) from e
        return response


fio_service = FioClient()

driver = get_driver()
@driver.on_shutdown
async def stop_fio_service() -> None:
    await fio_service.close()
