from enum import Enum
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelProfile(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"


ProfileName = Literal["fast", "balanced", "accurate"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    model_profile_fast: str = "gpt-4o-mini"
    model_profile_balanced: str = "gpt-4o"
    model_profile_accurate: str = "claude-sonnet-4-20250514"

    default_profile: ProfileName = "balanced"
    max_revisions: int = 0  # 0 = unlimited revisions
    max_repair_attempts: int = 2

    def get_model_for_profile(self, profile: ProfileName) -> str:
        mapping = {
            "fast": self.model_profile_fast,
            "balanced": self.model_profile_balanced,
            "accurate": self.model_profile_accurate,
        }
        return mapping[profile]

    def is_anthropic_model(self, model: str) -> bool:
        return model.startswith("claude")

    def has_api_keys(self) -> bool:
        return bool(self.openai_api_key or self.anthropic_api_key)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
