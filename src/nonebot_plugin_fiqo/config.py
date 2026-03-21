from nonebot import get_plugin_config
from pydantic import BaseModel, Field, SecretStr


class WeblateConfig(BaseModel):
    api_token: SecretStr | None = None


class FormatConfig(BaseModel):
    single_response_line_limit: int = 10
    single_response_char_limit: int = 400
    list_item_lead: str = " - "


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


class ScopedConfig(BaseModel):
    game: GameInfoConfig = Field(default_factory=GameInfoConfig)
    weblate: WeblateConfig = Field(default_factory=WeblateConfig)
    users: Users = Field(default_factory=Users)
    format: FormatConfig = Field(default_factory=FormatConfig)


class Config(BaseModel):
    """Plugin Config Here"""

    fiqo: ScopedConfig = Field(default_factory=ScopedConfig)


plugin_config = get_plugin_config(Config).fiqo
