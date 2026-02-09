from pydantic import (
    BaseModel,
    Field,
    RootModel,
    model_validator,
)

from . import exception


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
    desc:       str
    def __str__(self) -> str:
        return (f"代码：{self.ticker}\n"
                f"名称：{self.name}\n"
                f"类别：{self.category}\n"
                f"重量：{self.weight} t/吨\n"
                f"体积：{self.volume} m³/立方米\n"
                f"描述：{self.desc}")

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

class I18nCategories(RootModel):
    """
    I18nCategories represents all mappings of material categories original names
        to localized names, fetched from Weblate.
    """
    root: list[WeblateI18nUnit]

    def get_category_name(self, original_name: str) -> str:
        key_name = f"MaterialCategory.{''.join(original_name.split())}"
        for unit in self.root:
            if unit.key == key_name:
                return unit.target
        raise exception.I18nFetchError(original_name, "Category name not found")
