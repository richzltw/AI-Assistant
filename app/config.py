from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_id: str = Field(default="")
    region: str = Field(default="us-central1")
    service_name: str = Field(default="gcp-multimodal-assistant")

    # Primary LLM (Gemini)
    google_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")

    # Optional cross-cloud fallback model provider
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")

    # Optional external tools
    brave_search_api_key: str = Field(default="")
    function_router_url: str = Field(default="")
    function_router_token: str = Field(default="")

    # Runtime controls
    max_input_chars: int = Field(default=4000)
    shell_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
