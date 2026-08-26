from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TTS_BDS"
    prod: bool = False

    database_url_dev: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tts_bds"
    secret_key_dev: str = "dev-secret-key-change-me"

    database_url_prod: str = ""
    secret_key_prod: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def environment(self) -> str:
        return "production" if self.prod else "development"

    @property
    def debug(self) -> bool:
        return not self.prod

    @property
    def database_url(self) -> str:
        if self.prod:
            if not self.database_url_prod:
                raise ValueError("PROD=true but DATABASE_URL_PROD is not set")
            return self.database_url_prod
        return self.database_url_dev

    @property
    def secret_key(self) -> str:
        if self.prod:
            if not self.secret_key_prod:
                raise ValueError("PROD=true but SECRET_KEY_PROD is not set")
            return self.secret_key_prod
        return self.secret_key_dev


@lru_cache
def get_settings() -> Settings:
    return Settings()
