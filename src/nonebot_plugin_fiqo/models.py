import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    RootModel,
    field_validator,
    model_validator,
)

from nonebot_plugin_fiqo import exceptions

# =============================================
# Core DTOs
# =============================================


class MaterialDTO(BaseModel):
    ticker: str
    name: str
    category: str
    weight: float
    volume: float
    desc: str | None = None

    @classmethod
    def from_fio_response(cls, response: "FIOMaterialResponse") -> "MaterialDTO":
        return cls(
            ticker=response.ticker,
            name=response.name,
            category=response.category,
            weight=response.weight,
            volume=response.volume,
        )


class CostMaterialDTO(BaseModel):
    ticker: str
    amount: int


class RecipeDTO(BaseModel):
    string_representation: str
    duration: timedelta
    inputs: list[CostMaterialDTO]
    outputs: list[CostMaterialDTO]

    @classmethod
    def from_fio_response(cls, response: "Recipe") -> "RecipeDTO":
        return cls(
            string_representation=response.building + ":" + response.recipe_name,
            duration=response.duration,
            inputs=[
                CostMaterialDTO(ticker=i.ticker, amount=i.amount)
                for i in response.inputs
            ],
            outputs=[
                CostMaterialDTO(ticker=o.ticker, amount=o.amount)
                for o in response.outputs
            ],
        )


class BuildingDTO(BaseModel):
    ticker: str
    name: str
    desc: str | None = None
    expertise: str | None = None
    pioneers: int
    settlers: int
    technicians: int
    engineers: int
    scientists: int
    area: int
    cost: list[CostMaterialDTO]
    recipes: list[RecipeDTO]

    @classmethod
    def from_fio_response(cls, response: "FIOBuildingResponse") -> "BuildingDTO":
        return cls(
            ticker=response.ticker,
            name=response.name,
            expertise=response.expertise,
            pioneers=response.pioneers,
            settlers=response.settlers,
            technicians=response.technicians,
            engineers=response.engineers,
            scientists=response.scientists,
            area=response.area,
            cost=[
                CostMaterialDTO(ticker=cost.ticker, amount=cost.amount)
                for cost in response.cost
            ],
            recipes=[
                RecipeDTO(
                    string_representation=recipe.string_representation.replace(
                        "-", " "
                    ),
                    duration=recipe.duration,
                    inputs=[
                        CostMaterialDTO(ticker=i.ticker, amount=i.amount)
                        for i in recipe.inputs
                    ],
                    outputs=[
                        CostMaterialDTO(ticker=o.ticker, amount=o.amount)
                        for o in recipe.outputs
                    ],
                )
                for recipe in response.recipes
            ],
        )


class CXOrder(BaseModel):
    price: float
    amount: float


class CXMaterialDTO(BaseModel):
    ticker: str
    exchange: str
    currency: str
    price: float
    ask_price: float
    ask_size: int
    bid_price: float
    bid_size: int
    traded: int
    supply: int
    demand: int
    MM_buy: float | None
    MM_sell: float | None
    timestamp: datetime
    buy_orders: list[CXOrder]
    sell_orders: list[CXOrder]

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

    @classmethod
    def from_fio_response(cls, response: "FIOCXResponse") -> "CXMaterialDTO":
        return cls(
            ticker=response.ticker,
            exchange=response.exchange,
            currency=response.currency,
            price=response.price,
            ask_price=response.ask_price,
            ask_size=response.ask_size,
            bid_price=response.bid_price,
            bid_size=response.bid_size,
            traded=response.traded,
            supply=response.supply,
            demand=response.demand,
            MM_buy=response.MM_buy,
            MM_sell=response.MM_sell,
            timestamp=response.timestamp,
            buy_orders=[
                CXOrder(price=order.price, amount=order.amount)
                for order in response.buy_orders
            ],
            sell_orders=[
                CXOrder(price=order.price, amount=order.amount)
                for order in response.sell_orders
            ],
        )


class BasePlanetDTO(BaseModel):
    natrual_id: str
    name: str


class OfficePlanetDTO(BaseModel):
    natrual_id: str
    name: str


class UserAndCompanyDTO(BaseModel):
    user_id: str
    company_id: str
    username: str
    subscription_level: str
    company_name: str
    company_code: str
    corporation_name: str | None
    corporation_code: str | None
    rating: str
    created_days: int
    faction: str
    base_counts: int
    bases: list[BasePlanetDTO]
    offices: list[OfficePlanetDTO]

    @classmethod
    def from_fio_response(cls, response: "FIOUsrAndCoResponse") -> "UserAndCompanyDTO":
        return cls(
            user_id=response.user_id,
            company_id=response.company_id,
            username=response.username,
            subscription_level=response.subscription_level
            if response.subscription_level
            else "TRIAL",
            company_name=response.company_name,
            company_code=response.company_code,
            corporation_name=response.corporation_name,
            corporation_code=response.corporation_code,
            rating=response.rating,
            created_days=response.created_days,
            faction=response.faction,
            base_counts=response.base_counts,
            bases=[
                BasePlanetDTO(natrual_id=base.natrual_id, name=base.name)
                for base in response.bases
            ],
            offices=[
                OfficePlanetDTO(natrual_id=office.natrual_id, name=office.name)
                for office in response.current_offices
            ],
        )


# =============================================
# Inbound API Models
# =============================================


class FIOMaterialResponse(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def float_decision_limiter(cls, data: dict) -> dict:
        for key in ["Weight", "Volume"]:
            if key in data and isinstance(data[key], (int, float)):
                data[key] = round(float(data[key]), 3)
        return data

    ticker: str = Field(alias="Ticker")
    name: str = Field(alias="Name")
    category: str = Field(alias="CategoryName")
    weight: float = Field(alias="Weight")
    volume: float = Field(alias="Volume")


class FIOBuildingResponse(BaseModel):
    class BuildingCostMaterial(BaseModel):
        ticker: str = Field(alias="CommodityTicker")
        amount: int = Field(alias="Amount")

    class BuildingRecipe(BaseModel):
        string_representation: str = Field(alias="StandardRecipeName")
        duration: timedelta = Field(alias="DurationMs")
        inputs: list["FIOBuildingResponse.BuildingCostMaterial"] = Field(alias="Inputs")
        outputs: list["FIOBuildingResponse.BuildingCostMaterial"] = Field(
            alias="Outputs"
        )

        @model_validator(mode="before")
        @classmethod
        def convert_duration(cls, data: dict) -> dict:
            if "DurationMs" in data and isinstance(data["DurationMs"], int):
                data["DurationMs"] = timedelta(milliseconds=data.get("DurationMs", 0))
            return data

    ticker: str = Field(alias="Ticker")
    name: str = Field(alias="Name")
    expertise: str | None = Field(alias="Expertise")
    pioneers: int = Field(alias="Pioneers")
    settlers: int = Field(alias="Settlers")
    technicians: int = Field(alias="Technicians")
    engineers: int = Field(alias="Engineers")
    scientists: int = Field(alias="Scientists")
    area: int = Field(alias="AreaCost")
    cost: list[BuildingCostMaterial] = Field(alias="BuildingCosts")
    recipes: list[BuildingRecipe] = Field(alias="Recipes")


class RecipeMaterial(BaseModel):
    ticker: str = Field(alias="CommodityTicker")
    amount: int = Field(alias="Amount")


class Recipe(BaseModel):
    building: str = Field(alias="BuildingTicker")
    inputs: list[RecipeMaterial] = Field(alias="Inputs")
    outputs: list[RecipeMaterial] = Field(alias="Outputs")
    recipe_name: str = Field(alias="RecipeName")
    duration: timedelta = Field(alias="DurationMs")

    @model_validator(mode="before")
    @classmethod
    def convert_duration(cls, data: dict) -> dict:
        if "DurationMs" in data and isinstance(data["DurationMs"], int):
            data["DurationMs"] = timedelta(milliseconds=data.get("DurationMs", 0))
        return data


class FIORecipeResponse(RootModel[list[Recipe]]):
    pass


class FIOCXResponse(BaseModel):
    class FIOCXOrder(BaseModel):
        price: float = Field(alias="ItemCost")
        amount: float = Field(alias="ItemCount")

        @model_validator(mode="before")
        @classmethod
        def convert_mm_amount(cls, data: dict) -> dict:
            if data.get("ItemCount") is None and data.get("ItemCost") is not None:
                data["ItemCount"] = math.inf
            return data

    ticker: str = Field(alias="MaterialTicker")
    exchange: str = Field(alias="ExchangeCode")
    currency: str = Field(alias="Currency")
    price: float = Field(alias="Price")
    ask_price: float = Field(alias="Ask")
    ask_size: int = Field(alias="AskCount")
    bid_price: float = Field(alias="Bid")
    bid_size: int = Field(alias="BidCount")
    supply: int = Field(alias="Supply")
    demand: int = Field(alias="Demand")
    traded: int = Field(alias="Traded")
    MM_buy: float | None = Field(alias="MMBuy")
    MM_sell: float | None = Field(alias="MMSell")
    timestamp: datetime = Field(alias="Timestamp")
    buy_orders: list[FIOCXOrder] = Field(alias="BuyingOrders")
    sell_orders: list[FIOCXOrder] = Field(alias="SellingOrders")

    @model_validator(mode="before")
    @classmethod
    def order_cx_orders_by_price(cls, data: dict) -> dict:
        data["BuyingOrders"] = sorted(
            data.get("BuyingOrders", []),
            key=lambda order: order.get("ItemCost", 0),
            reverse=True,
        )
        data["SellingOrders"] = sorted(
            data.get("SellingOrders", []), key=lambda order: order.get("ItemCost", 0)
        )
        return data

    @field_validator(
        "price", "ask_price", "bid_price", "ask_size", "bid_size", mode="before"
    )
    @classmethod
    def handle_null_values(cls, value: float | None) -> float | int | None:
        if value is None:
            return 0
        return value


class FIOBasePlanetResponse(BaseModel):
    natrual_id: str = Field(alias="PlanetNaturalId")
    name: str = Field(alias="PlanetName")


class FIOOfficePlanetResponse(BaseModel):
    natrual_id: str = Field(alias="PlanetNaturalId")
    name: str = Field(alias="PlanetName")


class FIOUsrAndCoResponse(BaseModel):
    user_id: str = Field(alias="UserId")
    company_id: str = Field(alias="CompanyId")
    username: str = Field(alias="UserName")
    subscription_level: str | None = Field(alias="SubscriptionLevel")
    company_name: str = Field(alias="CompanyName")
    company_code: str = Field(alias="CompanyCode")
    corporation_name: str | None = Field(alias="CorporationName")
    corporation_code: str | None = Field(alias="CorporationCode")
    rating: str = Field(alias="OverallRating")
    created_days: int
    faction: str = Field(alias="CountryCode")
    base_counts: int
    bases: list[FIOBasePlanetResponse] = Field(alias="Planets")
    current_offices: list[FIOOfficePlanetResponse] = Field(alias="Offices")

    @model_validator(mode="before")
    @classmethod
    def calculate_created_days(cls, data: dict) -> dict:
        if isinstance(data, dict) and "CreatedEpochMs" in data:
            created_epoch_ms = data.get("CreatedEpochMs", 0)
            created_days = timedelta(
                milliseconds=(time.time() * 1000 - created_epoch_ms)
            ).days
            data["created_days"] = created_days
        return data

    @model_validator(mode="before")
    @classmethod
    def count_and_order_bases(cls, data: dict) -> dict:
        if isinstance(data, dict) and "Planets" in data:
            data["base_counts"] = len(data.get("Planets", []))
            data["Planets"] = sorted(
                data.get("Planets", []),
                key=lambda planet: planet.get("PlanetNaturalId", ""),
            )
        return data

    @model_validator(mode="before")
    @classmethod
    def remove_outdated_and_order_offices(cls, data: dict) -> dict:
        if isinstance(data, dict) and "Offices" in data:
            current_time = time.time() * 1000
            valid_offices = [
                o
                for o in data.get("Offices", [])
                if current_time - o.get("EndEpochMs", 0) < 0
            ]
            data["Offices"] = sorted(
                valid_offices,
                key=lambda office: office.get("OfficeNaturalId", ""),
            )
        return data


class I18nDictDTO(BaseModel):
    translations: dict[str, str]

    @model_validator(mode="before")
    @classmethod
    def extract_and_transform(cls, data: Any) -> Any:
        if isinstance(data, dict) and "results" in data:
            data = data.get("results", [])
            if len(data) == 0:
                raise exceptions.I18nFetchError("Weblate返回空列表")
            parsed_dict = {}
            for item in data:
                key = item.get("context", "")
                target_raw = item.get("target", [])
                target = (
                    "".join(target_raw)
                    if isinstance(target_raw, list)
                    else str(target_raw)
                )

                parsed_dict[key] = target
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
