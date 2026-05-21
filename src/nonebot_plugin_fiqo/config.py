from nonebot import get_plugin_config
from pydantic import Field, BaseModel, SecretStr


class WeblateConfig(BaseModel):
    api_token: SecretStr | None = None


class FormatConfig(BaseModel):
    single_response_line_limit: int = 10
    single_response_char_limit: int = 400
    list_item_lead: str = " - "


class CargoPresetConfig(BaseModel):
    weight: float
    volume: float
    display_name: str | None = None


class Users(BaseModel):
    admin: list[str] = Field(default_factory=list)
    superusers: list[str] = Field(default_factory=list)
    testusers: list[str] = Field(default_factory=list)
    group_level_threshold: int = 5


class GameInfoConfig(BaseModel):
    all_ingame_cxs: list[str] = Field(
        default_factory=lambda: ["AI1", "CI2", "CI1", "IC1", "NC2", "NC1"]
    )
    all_ingame_fas: dict[str, str] = Field(
        default_factory=lambda: {
            "AI": "AI",
            "CI": "CI",
            "IC": "IC",
            "NC": "NC",
            "INS": "IC",
            "NEO": "NC",
        }
    )
    cargo_presets: dict[str, CargoPresetConfig] = Field(
        default_factory=lambda: {
            "TCB": CargoPresetConfig(
                weight=100,
                volume=100,
                display_name="微型货舱套装",
            ),
            "VSC": CargoPresetConfig(
                weight=250,
                volume=250,
                display_name="超小货舱套装",
            ),
            "SCB": CargoPresetConfig(
                weight=500,
                volume=500,
                display_name="小型货舱套装",
            ),
            "MCB": CargoPresetConfig(
                weight=1000,
                volume=1000,
                display_name="中型货舱套装",
            ),
            "LCB": CargoPresetConfig(
                weight=2000,
                volume=2000,
                display_name="大型货舱套装",
            ),
            "HCB": CargoPresetConfig(
                weight=5000,
                volume=5000,
                display_name="巨型货舱套装",
            ),
            "VCB": CargoPresetConfig(
                weight=1000,
                volume=3000,
                display_name="高容积货舱套装",
            ),
            "WCB": CargoPresetConfig(
                weight=3000,
                volume=1000,
                display_name="高负荷货舱套装",
            ),
        }
    )


class ScopedConfig(BaseModel):
    game: GameInfoConfig = Field(default_factory=GameInfoConfig)
    weblate: WeblateConfig = Field(default_factory=WeblateConfig)
    users: Users = Field(default_factory=Users)
    format: FormatConfig = Field(default_factory=FormatConfig)


class Config(BaseModel):
    """Plugin Config Here"""

    fiqo: ScopedConfig = Field(default_factory=ScopedConfig)


plugin_config = get_plugin_config(Config).fiqo
