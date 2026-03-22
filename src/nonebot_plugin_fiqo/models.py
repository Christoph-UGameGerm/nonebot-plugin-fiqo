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
                "StandardRecipeName" not in data
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

    @model_validator(mode="after")
    def post_process_data(self) -> "UserAndCompanyDTO":
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
