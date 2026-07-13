"""
Core configuration using Pydantic Settings.
All settings are loaded from environment variables or .env file.
"""
from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "LLMOps Gateway AI"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production-min-32-chars!!"
    allowed_origins: Union[str, List[str]] = "http://localhost:3000,http://localhost:8000"
    api_v1_prefix: str = "/api/v1"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database
    database_url: str = "postgresql+asyncpg://llmops:llmops_pass@localhost:5432/llmops_db"
    sync_database_url: str = "postgresql://llmops:llmops_pass@localhost:5432/llmops_db"
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "llmops_memory"

    # LLM Provider API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    grok_api_key: Optional[str] = None

    # JWT
    jwt_secret_key: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # Encryption
    encryption_key: Optional[str] = None

    # Monitoring
    prometheus_port: int = 9090
    enable_metrics: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Cost Thresholds (USD)
    daily_cost_threshold_usd: float = 100.0
    monthly_cost_threshold_usd: float = 2000.0

    # Routing
    default_provider: str = "openai"
    fallback_provider: str = "anthropic"
    enable_cost_optimization: bool = True
    enable_auto_routing: bool = True

    # LLM Provider Costs per 1M tokens (USD) - as of 2024
    provider_costs: dict = {
        "openai": {"gpt-4o": {"input": 2.50, "output": 10.00}, "gpt-4o-mini": {"input": 0.15, "output": 0.60}},
        "anthropic": {"claude-3-5-sonnet": {"input": 3.00, "output": 15.00}, "claude-3-haiku": {"input": 0.25, "output": 1.25}},
        "gemini": {"gemini-2.5-pro": {"input": 1.25, "output": 5.00}, "gemini-2.5-flash": {"input": 0.075, "output": 0.30}},
        "mistral": {"mistral-large": {"input": 2.00, "output": 6.00}, "mistral-small": {"input": 0.20, "output": 0.60}},
    }

    # Context windows per model
    context_windows: dict = {
        "gpt-4o": 128000, "gpt-4o-mini": 128000,
        "claude-3-5-sonnet": 200000, "claude-3-haiku": 200000,
        "gemini-2.5-pro": 1000000, "gemini-2.5-flash": 1000000,
        "mistral-large": 128000, "mistral-small": 128000,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
