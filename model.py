from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    RootModel,
    model_validator,
)

from . import exception


class QueryErrorType(Enum):
    NETWORK = "bad_connection"
    TICKER = "wrong_ticker"
    I18N = "i18n_error"

class FIOMaterialResponse(BaseModel):
    """
    FIOMaterialResponse represents the response from FIO API for material information.
    It is used to parse the JSON response and extract relevant fields for material info.
    """
    ticker:     str     = Field(alias="Ticker")
    name:       str     = Field(alias="Name")
    category:   str     = Field(alias="MaterialCategoryId")
    weight:     float   = Field(alias="Weight")
    volume:     float   = Field(alias="Volume")

class FIOCategoriesResponse(RootModel):
    """
    FIOCategoriesResponse represents the response from FIO API for material categories.
    It is used to parse the JSON response and extract relevant fields for\
        material categories.
    """
    root: list[dict]

    def get_category_name(self, category_id: str) -> str:
        for category in self.root:
            if category["MaterialCategoryId"] == category_id:
                return category["CategoryName"]
        raise exception.CategoryNotFoundError(category_id)

class FIOBuildingResponse(BaseModel):
    """
    FIOBuildingResponse represents the response from FIO API for building information.
    It is used to parse the JSON response and extract relevant fields for building info.
    """
    class BuildingCostMaterial(BaseModel):
        ticker: str = Field(alias="Ticker")
        amount: int = Field(alias="Amount")

    class BuildingRecipe(BaseModel):
        string_representation:  str = Field(alias="BuildingRecipeId")
        duration_ms:            int = Field(alias="DurationMs")
        inputs: list["FIOBuildingResponse.BuildingCostMaterial"]\
                                    = Field(alias="Inputs")
        outputs:list["FIOBuildingResponse.BuildingCostMaterial"]\
                                    = Field(alias="Outputs")

    ticker:     str     = Field(alias="Ticker")
    name:       str     = Field(alias="Name")
    expertise:  str     = Field(alias="Expertise")
    pioneers:   int     = Field(alias="Pioneers")
    settlers:   int     = Field(alias="Settlers")
    technicians:int     = Field(alias="Technicians")
    engineers:  int     = Field(alias="Engineers")
    scientists: int     = Field(alias="Scientists")
    area:       int     = Field(alias="AreaCost")
    cost: list[BuildingCostMaterial]    = Field(alias="Costs")
    recipes: list[BuildingRecipe]       = Field(alias="Recipes")

class MaterialInfo(BaseModel):
    """
    MaterialInfo represents the information of a material fetched from FIO API.
    It also acts as the reply model for material information queries.
    """
    ticker:     str
    name:       str
    category:   str
    weight:     float
    volume:     float
    desc:       str | None = None
    def __str__(self) -> str:
        return (f"代码：{self.ticker}\n"
                f"名称：{self.name}\n"
                f"类别：{self.category}\n"
                f"重量：{self.weight} t/吨\n"
                f"体积：{self.volume} m³/立方米\n"
                f"描述：{self.desc}")

class BuildingInfo(BaseModel):
    """
    BuildingInfo represents the information of a building fetched from FIO API.
    """
    class BuildingCostMaterial(BaseModel):
        ticker: str
        amount: int

    class BuildingRecipe(BaseModel):
        string_representation:  str
        duration_ms:            int
        inputs:                 list["BuildingInfo.BuildingCostMaterial"]
        outputs:                list["BuildingInfo.BuildingCostMaterial"]

    ticker:     str
    name:       str
    desc:       str | None = None
    expertise:  str
    pioneers:   int
    settlers:   int
    technicians:int
    engineers:  int
    scientists: int
    area:       int
    cost:       list[BuildingCostMaterial]
    recipes:    list[BuildingRecipe]

    def __str__(self) -> str:
        cost_str = "\n".join(
            [f"  {cost_material.amount} {cost_material.ticker}"
             for cost_material in self.cost]
        )
        recipes_str = "\n".join(
            [f"  - {recipe.string_representation}\
             (耗时：{recipe.duration_ms // 1000}秒)"
             for recipe in self.recipes]
        )
        return (f"代码：{self.ticker}\n"
                + f"名称：{self.name}\n"
                + (f"专精：{self.expertise}\n" if self.expertise else "无")
                + (f"先驱者：{self.pioneers}\n" if self.pioneers > 0 else "")
                + (f"定居者：{self.settlers}\n" if self.settlers > 0 else "")
                + (f"职技工：{self.technicians}\n" if self.technicians > 0 else "")
                + (f"工程师：{self.engineers}\n" if self.engineers > 0 else "")
                + (f"科学家：{self.scientists}\n" if self.scientists > 0 else "")
                + f"占地面积：{self.area}\n"
                + f"建造材料：\n{cost_str}\n"
                + f"可用配方：\n{recipes_str}")

class WeblateI18nUnit(BaseModel):
    """
    WeblateI18nUnit represents a single translation unit fetched from Weblate.
    It is used to parse the response from Weblate API and extract localized terms.
    """
    key:    str = Field(alias="context")
    source: str = Field(alias="source")
    target: str = Field(alias="target")

    @model_validator(mode="before")
    @classmethod
    def concatenate_fields(cls, data: dict) -> dict:
        data["source"] = "".join(data.get("source", []))
        data["target"] = "".join(data.get("target", []))
        return data

class I18nMaterial(RootModel):
    """
    I18nMaterial represents the localized information of a material \
        fetched from Weblate.
    Typically, there is one translation unit for material name, \
        and one for material description.
    """
    root:   list[WeblateI18nUnit]

    @model_validator(mode="after")
    def check_not_empty(self) -> "I18nMaterial":
        if len(self.root) == 0:
            raise exception.I18nFetchError("I18nMaterial", "No translation found")
        return self

    def get_field(self, name: str, field: str) -> str:
        for unit in self.root:
            if unit.key.split(".")[-2] == name and unit.key.endswith(field):
                return unit.target
        raise exception.I18nFetchError(name, "Field not found")

class I18nBuilding(RootModel):
    """
    I18nBuilding represents the localized information of a building \
        fetched from Weblate.
    Typically, there is one translation unit for building name, \
        and one for building description.
    """
    root:   list[WeblateI18nUnit]

    @model_validator(mode="after")
    def check_not_empty(self) -> "I18nBuilding":
        if len(self.root) == 0:
            raise exception.I18nFetchError("I18nBuilding", "No translation found")
        return self

    @model_validator(mode="after")
    def replace_underscore_with_dot_in_key(self) -> "I18nBuilding":
        for unit in self.root:
            unit.key = unit.key.replace("_", ".")
        return self

    def get_field(self, name: str, field: str) -> str:
        for unit in self.root:
            if unit.key.split(".")[-2] == name and unit.key.endswith(field):
                return unit.target
        raise exception.I18nFetchError(name, "Field not found")

class I18nCategories(RootModel):
    """
    I18nCategories represents all mappings of material categories original names
        to localized names, fetched from Weblate.
    """
    root: list[WeblateI18nUnit]

    def get_category_name(self, original_name: str) -> str:
        """
        Get category name by original name.

        :param original_name: Category name from FIO API
        :type original_name: str
        :return: Localized category name
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the category name
        """
        key_name = f"MaterialCategory.{''.join(original_name.split())}"
        for unit in self.root:
            if unit.key == key_name:
                return unit.target
        raise exception.I18nFetchError(original_name, "Category name not found")

class I18nExpertise(RootModel):
    """
    I18nExpertise represents the localized name of AN expertise category \
        fetched from Weblate.
    """
    root: list[WeblateI18nUnit]

    def get_expertise_name(self, original_name: str) -> str:
        """
        Get expertise name by original name.

        :param original_name: Expertise name from FIO API
        :type original_name: str
        :return: Localized expertise name
        :rtype: str
        :raises I18nFetchError: If an error occurs while fetching the expertise name
        """
        key_name = f"ExpertiseCategory.{original_name}"
        for unit in self.root:
            if unit.key == key_name:
                return unit.target
        raise exception.I18nFetchError(original_name, "Expertise name not found")

@dataclass
class QueryResult:
    """
    Generic result object for queries.
    """
    id: str
    info: Any | None = None
    error_type: QueryErrorType | None = None

@dataclass
class MaterialQueryResult:
    """
    Result of a material query.
    """
    ticker: str
    info: MaterialInfo | None = None
    error_type: QueryErrorType | None = None
