from nonebot import get_plugin_config
from pydantic import BaseModel, SecretStr


class WeblateConfig(BaseModel):
    api_token: SecretStr


class FormatConfig(BaseModel):
    single_response_line_limit: int
    single_response_char_limit: int
    list_item_lead: str


class Users(BaseModel):
    admin: list[str] = []
    superusers: list[str] = []
    testusers: list[str] = []
    group_level_threshold: int


class ScopedConfig(BaseModel):
    all_ingame_cxs: list[str]
    weblate: WeblateConfig
    users: Users
    format: FormatConfig


class Config(BaseModel):
    """Plugin Config Here"""

    fiqo: ScopedConfig


plugin_config = get_plugin_config(Config).fiqo
