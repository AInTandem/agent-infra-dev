# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Round Table API Configuration"""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Round Table API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:7860"]

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/roundtable.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_decode_responses: bool = True

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
