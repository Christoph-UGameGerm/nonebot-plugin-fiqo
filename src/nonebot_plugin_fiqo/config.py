from nonebot import get_plugin_config
from pydantic import BaseModel, SecretStr


class WeblateConfig(BaseModel):
    api_token: SecretStr | None = None


class FormatConfig(BaseModel):
    single_response_line_limit: int = 10
    single_response_char_limit: int = 400
    list_item_lead: str = " - "


class Users(BaseModel):
    admin: list[str] = []
    superusers: list[str] = []
    testusers: list[str] = []
    group_level_threshold: int = 5


class GameInfoConfig(BaseModel):
    all_ingame_cxs: list[str] = ["AI1", "CI2", "CI1", "IC1", "NC2", "NC1"]
    all_ingame_fas: dict[str, str] = {
        "AI": "AI",
        "CI": "CI",
        "IC": "IC",
        "NC": "NC",
        "INS": "IC",
        "NEO": "NC",
    }


class ScopedConfig(BaseModel):
    game: GameInfoConfig
    weblate: WeblateConfig
    users: Users
    format: FormatConfig


class Config(BaseModel):
    """Plugin Config Here"""

    fiqo: ScopedConfig


plugin_config = get_plugin_config(Config).fiqo
