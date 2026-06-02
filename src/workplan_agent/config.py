import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Primary model for all agents (highest-accuracy defaults).
    model: str = "gpt-4o-mini"
    # Used when `model` is Claude but only OPENAI_API_KEY is configured.
    fallback_model: str = "gpt-5.5-pro"

    max_revisions: int = 0  # 0 = unlimited revisions
    max_repair_attempts: int = 2
    enable_prompt_cache: bool = True

    def is_anthropic_model(self, model: str) -> bool:
        return model.startswith("claude")

    def has_api_keys(self) -> bool:
        return bool(self.openai_api_key or self.anthropic_api_key)

    def resolve_model(self) -> str:
        model = self.model
        if self.is_anthropic_model(model):
            if self.anthropic_api_key:
                return model
            if self.openai_api_key:
                warnings.warn(
                    f"Model '{model}' requires ANTHROPIC_API_KEY. "
                    f"Falling back to {self.fallback_model}.",
                    stacklevel=2,
                )
                return self.fallback_model
            raise ValueError(
                f"Model '{model}' requires ANTHROPIC_API_KEY. "
                "Set ANTHROPIC_API_KEY or override MODEL to an OpenAI model."
            )

        if self.openai_api_key:
            return model
        if self.anthropic_api_key:
            anthropic_model = (
                self.model
                if self.is_anthropic_model(self.model)
                else "claude-opus-4-8"
            )
            warnings.warn(
                f"Model '{model}' requires OPENAI_API_KEY. Using {anthropic_model} instead.",
                stacklevel=2,
            )
            return anthropic_model
        raise ValueError(
            f"Model '{model}' requires OPENAI_API_KEY. "
            "Set OPENAI_API_KEY or override MODEL to a Claude model."
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
