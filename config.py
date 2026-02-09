from pydantic import BaseModel, SecretStr


class ScopedConfig(BaseModel):
    weblate_api_token: SecretStr

class Config(BaseModel):
    """Plugin Config Here"""
    fiqo: ScopedConfig
