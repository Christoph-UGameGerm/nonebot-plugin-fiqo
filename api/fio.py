from nonebot import get_driver
from pydantic import BaseModel

from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.api import BaseClient
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.exceptions import (
    WrongBuildingTickerError,
    WrongCXTickerError,
    WrongMaterialTickerError,
    WrongRecipeTickerError,
)
from fiqo_nonebot_plugin_dev.plugins.nonebot_plugin_fiqo.models import (
    FIOBuildingResponse,
    FIOCXResponse,
    FIOMaterialResponse,
    FIORecipeResponse,
)


class FioEndpoint(BaseModel):
    base_url: str = "https://rest.fnar.net"
    material: str = "/material/"
    building: str = "/building/"
    cx: str = "/exchange/"
    recipes: str = "/recipes/"


ENDPOINTS = FioEndpoint()


class FioClient(BaseClient):
    def __init__(self) -> None:
        super().__init__(base_url=ENDPOINTS.base_url, timeout=10)
        self.client.headers.update({"User-Agent": "CommunityBot/FioClient"})

    async def get_recipe_info(self, ticker: str) -> FIORecipeResponse:
        return await self.request(
            key_and_model=(f"fio:recipe:{ticker}", FIORecipeResponse),
            endpoint=f"{ENDPOINTS.recipes}{ticker}",
            params=None,
            not_found_error=WrongRecipeTickerError(ticker),
            ttl=86400,
        )

    async def get_material_info(self, ticker: str) -> FIOMaterialResponse:
        return await self.request(
            key_and_model=(f"fio:mat:{ticker}", FIOMaterialResponse),
            endpoint=f"{ENDPOINTS.material}{ticker}",
            params=None,
            not_found_error=WrongMaterialTickerError(ticker),
            ttl=86400,
        )

    async def get_building_info(self, ticker: str) -> FIOBuildingResponse:
        return await self.request(
            key_and_model=(f"fio:bui:{ticker}", FIOBuildingResponse),
            endpoint=f"{ENDPOINTS.building}{ticker}",
            params=None,
            not_found_error=WrongBuildingTickerError(ticker),
            ttl=86400,
        )

    async def get_cx_material_info(self, ticker: str) -> FIOCXResponse:
        return await self.request(
            key_and_model=(
                f"fio:cx:{ticker}",
                FIOCXResponse,
            ),
            endpoint=f"{ENDPOINTS.cx}{ticker}",
            params={"include_buy_orders": "true", "include_sell_orders": "true"},
            not_found_error=WrongCXTickerError(ticker),
            ttl=60,
        )


fio_client = FioClient()


@get_driver().on_shutdown
async def shutdown_fio_client() -> None:
    await fio_client.close()
