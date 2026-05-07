from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    github_token: str
    anthropic_api_key: str
    supabase_url: str
    supabase_key: str

    github_keywords: list[str] = ["refactor", "optimization", "experimental"]
    trace_prompt_version: int = 1
    anthropic_model: str = "claude-sonnet-4-6"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
