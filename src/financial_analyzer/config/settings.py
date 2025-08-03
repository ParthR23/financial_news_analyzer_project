"""Centralized application configuration using Pydantic Settings.

All configuration values are sourced from environment variables and an optional
`.env` file located at the project root. This avoids hard-coding secrets in the
codebase while still providing a single import for configuration throughout the
application.
"""
from pathlib import Path
from typing import Optional

try:
    # Pydantic v2 style settings
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback to Pydantic v1
    from pydantic import BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore


class Settings(BaseSettings):
    """Application-wide settings resolved from environment variables."""

    # General application metadata
    PROJECT_NAME: str = "Financial News Analyzer"

    # AWS / S3
    S3_BUCKET_NAME: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str

    # Large Language Model / embedding services
    LLM_API_KEY: str

    # Vector database location (e.g., for ChromaDB)
    VECTOR_DB_PATH: Path

    # Pydantic v2 configuration (if available)
    if SettingsConfigDict is not None:  # pragma: no cover
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

    class Config:  # noqa: D106  # Pydantic v1 fallback
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# A single shared instance that can be imported throughout the codebase
settings = Settings()
