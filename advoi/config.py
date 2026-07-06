"""Central configuration loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    advoi_env: str = "development"
    advoi_log_level: str = "INFO"
    database_url: str = "postgresql://advoi:advoi@localhost:5432/advoi"
    redis_url: str = "redis://localhost:6379/0"
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    default_model: str = "gpt-4o-mini"
    advoi_confirmation_required: bool = True


settings = Settings()