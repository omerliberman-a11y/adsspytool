from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Storage
    database_url: str

    # Meta Graph API (free, official)
    meta_graph_token: SecretStr = Field(default=SecretStr(""))
    meta_graph_api_version: str = "v21.0"

    # AI providers (all free tier)
    gemini_api_key: SecretStr = Field(default=SecretStr(""))
    groq_api_key: SecretStr = Field(default=SecretStr(""))
    cf_account_id: str = ""
    cf_api_token: SecretStr = Field(default=SecretStr(""))

    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "qwen2.5:14b-instruct"
    ollama_vision_model: str = "llama3.2-vision:11b"

    # Router preferences
    ai_text_primary: str = "groq"
    ai_vision_primary: str = "gemini"
    ai_embedding_primary: str = "local"
    local_only: bool = False

    # Object storage (Cloudflare R2 — 10 GB free, zero egress)
    r2_account_id: str = ""
    r2_access_key_id: SecretStr = Field(default=SecretStr(""))
    r2_secret_access_key: SecretStr = Field(default=SecretStr(""))
    r2_bucket: str = "adspy-media"
    r2_endpoint: str = ""

    # Capture-replay sessions
    session_store_dir: str = "./local-cache/sessions"

    # Scrape limits
    scrape_max_items_per_run: int = 2000
    scrape_timeout_secs: int = 600

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    def __repr__(self) -> str:
        return (
            "Settings("
            f"database_url={self.database_url!r}, "
            f"ai_text_primary={self.ai_text_primary!r}, "
            f"ai_vision_primary={self.ai_vision_primary!r}, "
            "secrets=***)"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
