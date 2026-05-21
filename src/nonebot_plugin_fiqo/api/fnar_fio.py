from nonebot import get_driver
from pydantic import BaseModel

from nonebot_plugin_fiqo.models import FnarCompanyLookupDTO
from nonebot_plugin_fiqo.exceptions import WrongUsernameOrCompanyTickerError

from .base_client import BaseClient


class FnarEndpoint(BaseModel):
    base_url: str = "https://api.fnar.net"
    company_lookup: str = "/company/lookup"


ENDPOINTS = FnarEndpoint()


class FnarFioClient(BaseClient):
    def __init__(self) -> None:
        super().__init__(base_url=ENDPOINTS.base_url, timeout=10)
        self.client.headers.update({"User-Agent": "CommunityBot/FnarFioClient"})

    async def get_company_lookup(self, company_code: str) -> FnarCompanyLookupDTO:
        not_found_error = WrongUsernameOrCompanyTickerError(company_code)
        response = await self.request(
            key_and_model=(
                f"fnar:company_lookup:{company_code}",
                list[FnarCompanyLookupDTO | None],
            ),
            endpoint=ENDPOINTS.company_lookup,
            params={
                "company": company_code,
                "include_planets": "true",
                "include_offices": "true",
            },
            not_found_error=not_found_error,
            ttl=600,
        )
        company = next((item for item in response if item is not None), None)
        if company is None:
            raise not_found_error
        return company


fnar_fio_client = FnarFioClient()


@get_driver().on_shutdown
async def shutdown_fnar_fio_client() -> None:
    await fnar_fio_client.close()
