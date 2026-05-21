import math
import time
from typing import Any
from datetime import datetime, timezone, timedelta
from dataclasses import field, dataclass

from pydantic import (
    Field,
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
)

# =============================================
# Core DTOs
# =============================================


class FIQOBaseDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class MaterialDTO(FIQOBaseDTO):
    ticker: str = Field(validation_alias="Ticker")
    name: str = Field(validation_alias="Name")
    category: str = Field(validation_alias="CategoryName")
    weight: float = Field(validation_alias="Weight")
    volume: float = Field(validation_alias="Volume")
    desc: str | None = None

    @field_validator("weight", "volume", mode="before")
    @classmethod
    def round_float(cls, v: Any) -> Any:
        if isinstance(v, (int, float)):
            return round(float(v), 3)
        return v


class FitResultDTO(FIQOBaseDTO):
    ticker: str
    material_name: str
    max_units: int
    remaining_weight: float
    remaining_volume: float
    limiting_factor: str
    unit_weight: float
    unit_volume: float
    preset_key: str | None = None
    preset_name: str | None = None
    preset_weight: float | None = None
    preset_volume: float | None = None


class FitRatioItemDTO(FIQOBaseDTO):
    ticker: str
    amount: int
    unit_weight: float
    unit_volume: float
    total_weight: float
    total_volume: float


class FitRatioResultDTO(FIQOBaseDTO):
    max_groups: int
    remaining_weight: float
    remaining_volume: float
    limiting_factor: str
    group_weight: float
    group_volume: float
    items: list[FitRatioItemDTO]
    preset_key: str | None = None
    preset_name: str | None = None
    preset_weight: float | None = None
    preset_volume: float | None = None


class CostMaterialDTO(FIQOBaseDTO):
    ticker: str = Field(validation_alias="CommodityTicker")
    amount: int = Field(validation_alias="Amount")


class RecipeDTO(FIQOBaseDTO):
    string_representation: str = Field(validation_alias="StandardRecipeName")
    duration: timedelta = Field(validation_alias="DurationMs")
    inputs: list[CostMaterialDTO] = Field(validation_alias="Inputs")
    outputs: list[CostMaterialDTO] = Field(validation_alias="Outputs")

    @model_validator(mode="before")
    @classmethod
    def _assemble_recipe_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # /recipes/ does not return StandardRecipeName
            # instead manually assembled from BuildingTicker and RecipeName
            if (
                not data.get("StandardRecipeName")
                and "BuildingTicker" in data
                and "RecipeName" in data
            ):
                data["StandardRecipeName"] = (
                    f"{data['BuildingTicker']}:{data['RecipeName']}"
                )
        return data

    @field_validator("duration", mode="before")
    @classmethod
    def convert_duration(cls, v: Any) -> timedelta:
        if isinstance(v, int):
            return timedelta(milliseconds=v)
        return v

    @field_validator("string_representation", mode="after")
    @classmethod
    def format_name(cls, v: str) -> str:
        return v.replace("-", " ")


class BuildingDTO(FIQOBaseDTO):
    ticker: str = Field(validation_alias="Ticker")
    name: str = Field(validation_alias="Name")
    desc: str | None = None
    expertise: str | None = Field(default=None, validation_alias="Expertise")
    pioneers: int = Field(validation_alias="Pioneers")
    settlers: int = Field(validation_alias="Settlers")
    technicians: int = Field(validation_alias="Technicians")
    engineers: int = Field(validation_alias="Engineers")
    scientists: int = Field(validation_alias="Scientists")
    area: int = Field(validation_alias="AreaCost")
    cost: list[CostMaterialDTO] = Field(validation_alias="BuildingCosts")
    recipes: list[RecipeDTO] = Field(validation_alias="Recipes")


class CXOrder(FIQOBaseDTO):
    company_code: str = Field(validation_alias="CompanyCode")
    price: float = Field(validation_alias="ItemCost")
    amount: float = Field(validation_alias="ItemCount")

    @field_validator("amount", mode="before")
    @classmethod
    def handle_null_amount(cls, v: Any) -> float:
        if v is None:
            return math.inf
        return float(v)


class CXMaterialDTO(FIQOBaseDTO):
    ticker: str = Field(validation_alias="MaterialTicker")
    exchange: str = Field(validation_alias="ExchangeCode")
    currency: str = Field(validation_alias="Currency")
    price: float = Field(validation_alias="Price")
    ask_price: float = Field(validation_alias="Ask")
    ask_size: int = Field(validation_alias="AskCount")
    bid_price: float = Field(validation_alias="Bid")
    bid_size: int = Field(validation_alias="BidCount")
    traded: int = Field(validation_alias="Traded")
    supply: int = Field(validation_alias="Supply")
    demand: int = Field(validation_alias="Demand")
    MM_buy: float | None = Field(validation_alias="MMBuy")
    MM_sell: float | None = Field(validation_alias="MMSell")
    timestamp: datetime = Field(validation_alias="Timestamp")
    buy_orders: list[CXOrder] = Field(validation_alias="BuyingOrders")
    sell_orders: list[CXOrder] = Field(validation_alias="SellingOrders")

    @computed_field
    @property
    def time_since_update(self) -> timedelta:
        return datetime.now(timezone.utc) - self.timestamp

    @field_validator(
        "price", "ask_price", "bid_price", "ask_size", "bid_size", mode="before"
    )
    @classmethod
    def handle_null_values(cls, value: float | None) -> float | int:
        if value is None:
            return 0
        return value

    @model_validator(mode="after")
    def order_cx_orders_by_price(self) -> "CXMaterialDTO":
        self.buy_orders.sort(key=lambda o: o.price, reverse=True)
        self.sell_orders.sort(key=lambda o: o.price)
        return self

    def get_buy_cost_for_amount(self, amount: float) -> tuple[float | None, float]:
        total_cost = 0.0
        remaining_amount = amount
        for order in self.sell_orders:
            if order.amount >= remaining_amount:
                total_cost += remaining_amount * order.price
                return total_cost, 0
            total_cost += order.amount * order.price
            remaining_amount -= order.amount
        return total_cost, remaining_amount

    def get_sell_revenue_for_amount(self, amount: float) -> tuple[float | None, float]:
        min_sell_price = min(
            filter(None, [self.ask_price, self.MM_sell, self.price]), default=0.0
        )
        return min_sell_price * amount, 0.0 if min_sell_price > 0 else amount


class BasePlanetDTO(FIQOBaseDTO):
    natural_id: str = Field(validation_alias="PlanetNaturalId")
    name: str = Field(validation_alias="PlanetName")


class OfficePlanetDTO(FIQOBaseDTO):
    natural_id: str = Field(validation_alias="PlanetNaturalId")
    name: str = Field(validation_alias="PlanetName")
    end_epoch_ms: int = Field(default=0, validation_alias="EndEpochMs")


class UserAndCompanyDTO(FIQOBaseDTO):
    user_id: str = Field(validation_alias="UserId")
    company_id: str = Field(validation_alias="CompanyId")
    username: str = Field(validation_alias="UserName")
    subscription_level: str = Field(validation_alias="SubscriptionLevel")
    company_name: str = Field(validation_alias="CompanyName")
    company_code: str = Field(validation_alias="CompanyCode")
    corporation_name: str | None = Field(
        default=None, validation_alias="CorporationName"
    )
    corporation_code: str | None = Field(
        default=None, validation_alias="CorporationCode"
    )
    rating: str = Field(validation_alias="OverallRating")
    created_epoch_ms: int = Field(default=0, validation_alias="CreatedEpochMs")
    faction: str = Field(validation_alias="CountryCode")
    base_counts: int = Field(default=0)
    bases: list[BasePlanetDTO] = Field(default_factory=list, validation_alias="Planets")
    offices: list[OfficePlanetDTO] = Field(
        default_factory=list, validation_alias="Offices"
    )

    @computed_field
    @property
    def created_days(self) -> int:
        if self.created_epoch_ms == 0:
            return 0
        return timedelta(milliseconds=time.time() * 1000 - self.created_epoch_ms).days

    @field_validator("subscription_level", mode="before")
    @classmethod
    def handle_sub_level(cls, v: Any) -> str:
        return v if v else "TRIAL"

    def refresh_company_locations(self) -> "UserAndCompanyDTO":
        self.base_counts = len(self.bases)
        self.bases.sort(key=lambda p: p.natural_id)

        current_ms = time.time() * 1000
        self.offices = sorted(
            [
                o
                for o in self.offices
                if o.end_epoch_ms == 0 or o.end_epoch_ms > current_ms
            ],
            key=lambda o: o.natural_id,
        )
        return self

    @model_validator(mode="after")
    def post_process_data(self) -> "UserAndCompanyDTO":
        return self.refresh_company_locations()


class FnarCompanyLookupDTO(FIQOBaseDTO):
    company_name: str = Field(validation_alias="Name")
    company_code: str = Field(validation_alias="Code")
    username: str = Field(validation_alias="UserName")
    faction: str = Field(validation_alias="CountryCode")
    corporation_name: str | None = Field(
        default=None, validation_alias="CorporationName"
    )
    corporation_code: str | None = Field(
        default=None, validation_alias="CorporationCode"
    )
    rating: str = Field(validation_alias="OverallRating")
    founded: datetime = Field(validation_alias="Founded")
    bases: list[BasePlanetDTO] = Field(default_factory=list, validation_alias="Planets")
    offices: list[OfficePlanetDTO] = Field(
        default_factory=list, validation_alias="Offices"
    )


class PlanetResourceDTO(FIQOBaseDTO):
    type: str = Field(validation_alias="resource_type")
    factor: float
    ticker: str = Field(validation_alias="material_ticker")
    daily_extraction: float
    max_extraction_in_world: float = Field(validation_alias="max_daily_extraction")


class CoGCProgramDTO(FIQOBaseDTO):
    type: str | None = Field(default=None, validation_alias="program_type")
    start_epoch_ms: int = Field(validation_alias="start_epochms")
    end_epoch_ms: int = Field(validation_alias="end_epochms")

    @computed_field
    @property
    def time_until_start(self) -> timedelta:
        return timedelta(milliseconds=self.start_epoch_ms - time.time() * 1000)

    @computed_field
    @property
    def time_until_end(self) -> timedelta:
        return timedelta(milliseconds=self.end_epoch_ms - time.time() * 1000)


class PlannerPlanetDTO(FIQOBaseDTO):
    natural_id: str = Field(validation_alias="planet_natural_id")
    name: str | None = Field(default=None, validation_alias="planet_name")
    system_id: str
    faction: str | None = Field(default=None, validation_alias="faction_code")
    has_rock_surface: bool = Field(validation_alias="surface")
    fertility: float
    gravity: float
    temperature: float
    pressure: float
    has_adm: bool = Field(validation_alias="has_administrationcenter")
    has_cogc: bool = Field(validation_alias="has_chamberofcommerce")
    has_localmarket: bool
    has_warehouse: bool
    has_shipyard: bool
    cogc_status: str | None = Field(
        default=None, validation_alias="cogc_program_status"
    )
    active_cogc_program_type: str | None = None
    resources: list[PlanetResourceDTO] = Field(default_factory=list)
    cogc_programs: list[CoGCProgramDTO] = Field(default_factory=list)
    cogc_program: CoGCProgramDTO | None = None

    @model_validator(mode="after")
    def select_current_cogc_program(self) -> "PlannerPlanetDTO":
        if self.active_cogc_program_type:
            self.cogc_program = next(
                (
                    p
                    for p in self.cogc_programs
                    if p.type == self.active_cogc_program_type
                ),
                None,
            )
            if self.cogc_program is not None:
                return self

        current_ms = time.time() * 1000
        active_programs = [
            p
            for p in self.cogc_programs
            if p.start_epoch_ms <= current_ms < p.end_epoch_ms
        ]

        if self.cogc_program is None and active_programs:
            self.cogc_program = max(active_programs, key=lambda p: p.start_epoch_ms)
        return self


class PlanetDTO(FIQOBaseDTO):
    natural_id: str
    name: str | None = None
    system_id: str
    system_name: str | None = None
    system_natural_id: str | None = None
    faction: str | None = None
    has_rock_surface: bool
    fertility: float
    gravity: float
    temperature: float
    pressure: float
    has_adm: bool
    has_cogc: bool
    has_localmarket: bool
    has_warehouse: bool
    has_shipyard: bool
    cogc_status: str | None = None
    resources: list[PlanetResourceDTO] = Field(default_factory=list)
    cogc_program: CoGCProgramDTO | None = None

    @computed_field
    @property
    def fertility_percent(self) -> float:
        if self.fertility == -1:
            return 0.0
        return 100 + 30.3 * self.fertility

    @computed_field
    @property
    def system_display_name(self) -> str:
        if (
            self.system_name
            and self.system_natural_id
            and self.system_name != self.system_natural_id
        ):
            return f"{self.system_name} ({self.system_natural_id})"
        if self.system_name:
            return self.system_name
        if self.system_natural_id:
            return self.system_natural_id
        return self.system_id

    @computed_field
    @property
    def type_display(self) -> str:
        if self.has_rock_surface:
            return "岩质（MCG x4/面积）"
        return "气态（AEF x面积/3）"

    @computed_field
    @property
    def gravity_display(self) -> str:
        if self.gravity < 0.25:
            return f"{self.gravity:.2f}（低重力，MGC x1/建筑）"
        if self.gravity > 2.5:
            return f"{self.gravity:.2f}（高重力，BL x1/建筑）"
        return f"{self.gravity:.2f}（适宜）"

    @computed_field
    @property
    def temperature_display(self) -> str:
        if self.temperature < -25:
            return f"{self.temperature:.2f}（低温，INS x10/面积）"
        if self.temperature > 75:
            return f"{self.temperature:.2f}（高温，TSH x1/建筑）"
        return f"{self.temperature:.2f}（适宜）"

    @computed_field
    @property
    def pressure_display(self) -> str:
        if self.pressure < 0.25:
            return f"{self.pressure:.2f}（低压，SEA x1/面积）"
        if self.pressure > 2.0:
            return f"{self.pressure:.2f}（高压，HSE x1/建筑）"
        return f"{self.pressure:.2f}（适宜）"

    @classmethod
    def from_planner(
        cls,
        planner: PlannerPlanetDTO,
    ) -> "PlanetDTO":
        return cls(
            natural_id=planner.natural_id,
            name=planner.name,
            system_id=planner.system_id,
            faction=planner.faction,
            has_rock_surface=planner.has_rock_surface,
            fertility=planner.fertility,
            gravity=planner.gravity,
            temperature=planner.temperature,
            pressure=planner.pressure,
            has_adm=planner.has_adm,
            has_cogc=planner.has_cogc,
            has_localmarket=planner.has_localmarket,
            has_warehouse=planner.has_warehouse,
            has_shipyard=planner.has_shipyard,
            cogc_status=planner.cogc_status,
            resources=planner.resources,
            cogc_program=planner.cogc_program,
        )


class SystemDTO(FIQOBaseDTO):
    natural_id: str = Field(validation_alias="SystemNaturalId")
    name: str = Field(validation_alias="SystemName")
    meteoroid_density: float = Field(validation_alias="MeteoroidDensity")


class SystemPlanetSummaryDTO(FIQOBaseDTO):
    natural_id: str
    name: str | None = None
    cogc_type: str | None = None


class SystemInfoDTO(FIQOBaseDTO):
    system: SystemDTO
    planets: list[SystemPlanetSummaryDTO] = Field(default_factory=list)


class I18nDictDTO(BaseModel):
    translations: dict[str, str]

    @model_validator(mode="before")
    @classmethod
    def extract_and_transform(cls, data: Any) -> Any:
        if isinstance(data, dict) and "results" in data:
            results = data["results"]

            parsed_dict = {}
            for item in results:
                key = item.get("context", "")
                target = item.get("target", "")
                parsed_dict[key] = (
                    "".join(target) if isinstance(target, list) else str(target)
                )
            return {"translations": parsed_dict}
        return data


# =============================================
# Outbound Service Models
# =============================================


@dataclass
class ServiceResult:
    contents: list[str] = field(default_factory=list)
    warnings: list[Exception] = field(default_factory=list)

    @property
    def is_perfect(self) -> bool:
        return len(self.warnings) == 0
