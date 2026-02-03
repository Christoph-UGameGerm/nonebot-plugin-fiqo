from pydantic import BaseModel, Field


class MaterialInfo(BaseModel):
    ticker: str = Field(alias="Ticker")
    name: str = Field(alias="Name")
    category: str = Field(alias="MaterialCategoryId")
    weight: float = Field(alias="Weight")
    volume: float = Field(alias="Volume")

    def __str__(self) -> str:
        return (f"代码：{self.ticker}\n"
                f"名称：{self.name}\n"
                f"类别：{self.category}\n"
                f"重量：{self.weight} t/吨\n"
                f"体积：{self.volume} m³/立方米")
