from nonebot import get_driver
from pydantic import BaseModel

from nonebot_plugin_fiqo.models import PlannerPlanetDTO
from nonebot_plugin_fiqo.exceptions import (
    PlanetNotFoundError,
)

from .base_client import BaseClient


class PrunPlannerEndpoint(BaseModel):
    base_url: str = "https://api.prunplanner.org/"
    planets: str = "/data/planets/"


ENDPOINTS = PrunPlannerEndpoint()


class PrunPlannerClient(BaseClient):
    def __init__(self) -> None:
        super().__init__(PrunPlannerEndpoint().base_url, timeout=10)
        self.client.headers.update({"User-Agent": "CommunityBot/PrunPlannerClient"})

    async def get_planet_info(self, name_or_id: str) -> list[PlannerPlanetDTO]:
        return await self.request(
            key_and_model=(f"prpl:planet:{name_or_id}", list[PlannerPlanetDTO]),
            endpoint=f"{ENDPOINTS.planets}{name_or_id}/",
            params=None,
            not_found_error=PlanetNotFoundError(name_or_id),
            ttl=None,
        )


planner_client = PrunPlannerClient()


@get_driver().on_shutdown
async def shutdown_planner_client() -> None:
    await planner_client.close()
