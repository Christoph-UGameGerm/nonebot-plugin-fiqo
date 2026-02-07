from typing import Any, Optional

import httpx
from nonebot import get_driver, logger
from pydantic import BaseModel

from . import exception


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
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": "CommunityBot/FioClient/v0.1"
                }
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

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

    async def get_material_info(self, material_tickers: list[str]) -> Any:
        logger.debug(f"Fetching material info for tickers: {material_tickers}")
        endpoint = ENDPOINTS.material
        params = {
            "ticker": material_tickers
        }
        try:
            response = await self._request(endpoint, params=params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.BAD_REQUEST:
                raise exception.WrongMaterialTickerError(material_tickers) from e
            raise
        except httpx.RequestError as e:
            raise exception.BadConnectionError(str(e)) from e
        else:
            return response


fio_service = FioClient()

driver = get_driver()
@driver.on_shutdown
async def stop_fio_service() -> None:
    await fio_service.close()
