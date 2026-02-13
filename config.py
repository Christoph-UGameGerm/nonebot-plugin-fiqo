from pydantic import BaseModel, SecretStr


class ScopedConfig(BaseModel):
    weblate_api_token: SecretStr
    longest_single_response: int

class Config(BaseModel):
    """Plugin Config Here"""
    fiqo: ScopedConfig
