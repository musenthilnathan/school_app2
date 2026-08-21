from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TTS_BDS"
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql://tts_user:tts_pass@localhost:5432/tts_bds"
    secret_key: str = "dev-secret-key-change-me"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
