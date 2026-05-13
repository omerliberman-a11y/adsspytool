from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required
    apify_token: SecretStr = Field(default=SecretStr(""))
    database_url: str
    redis_url: str

    # AI (later phases)
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    gemini_api_key: SecretStr = Field(default=SecretStr(""))
    openai_api_key: SecretStr = Field(default=SecretStr(""))

    # Object storage
    r2_account_id: str = ""
    r2_access_key_id: SecretStr = Field(default=SecretStr(""))
    r2_secret_access_key: SecretStr = Field(default=SecretStr(""))
    r2_bucket: str = "adspy-media"
    r2_endpoint: str = ""

    # Cost controls
    apify_max_usd_per_run: float = 5.00
    apify_timeout_secs: int = 600

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    def __repr__(self) -> str:
        return (
            "Settings("
            f"database_url={self.database_url!r}, "
            f"redis_url={self.redis_url!r}, "
            f"apify_token=***, anthropic_api_key=***, "
            f"log_level={self.log_level!r})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
