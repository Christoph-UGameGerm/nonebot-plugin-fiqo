from nonebot import get_driver
from pydantic import BaseModel

from nonebot_plugin_fiqo.models import (
    FIOCXResponse,
    FIORecipeResponse,
    FIOBuildingResponse,
    FIOMaterialResponse,
    FIOUsrAndCoResponse,
)
from nonebot_plugin_fiqo.exceptions import (
    WrongCXTickerError,
    WrongRecipeTickerError,
    WrongBuildingTickerError,
    WrongMaterialTickerError,
    WrongUsernameOrCompanyTickerError,
)

from .base_client import BaseClient


class FioEndpoint(BaseModel):
    base_url: str = "https://rest.fnar.net"
    material: str = "/material/"
    building: str = "/building/"
    cx: str = "/exchange/"
    recipes: str = "/recipes/"
    co_usr_username: str = "/user/"
    co_usr_company_code: str = "/company/code/"
    co_usr_company_name: str = "/company/name/"


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

    async def get_user_and_company_info(
        self,
        username: str | None = None,
        company_name: str | None = None,
        company_code: str | None = None,
    ) -> FIOUsrAndCoResponse:
        not_found_error = WrongUsernameOrCompanyTickerError(
            username or company_name or company_code or "未知"
        )
        if username:
            endpoint = f"{ENDPOINTS.co_usr_username}{username}"
            cache_key = f"fio:username:{username}"
        elif company_code:
            endpoint = f"{ENDPOINTS.co_usr_company_code}{company_code}"
            cache_key = f"fio:co_code:{company_code}"
        elif company_name:
            endpoint = f"{ENDPOINTS.co_usr_company_name}{company_name}"
            cache_key = f"fio:co_name:{company_name}"
        else:
            raise not_found_error
        return await self.request(
            key_and_model=(
                cache_key,
                FIOUsrAndCoResponse,
            ),
            endpoint=endpoint,
            params=None,
            not_found_error=not_found_error,
            ttl=None,
        )


fio_client = FioClient()


@get_driver().on_shutdown
async def shutdown_fio_client() -> None:
    await fio_client.close()
