"""Centralized application configuration using Pydantic Settings.

All configuration values are sourced from environment variables and an optional
`.env` file located at the project root. This avoids hard-coding secrets in the
codebase while still providing a single import for configuration throughout the
application.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application settings by loading them from environment variables
    or a .env file.
    """
    PROJECT_NAME: str = "Financial News Analyzer"
    S3_BUCKET_NAME: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    LLM_API_KEY: str
    VECTOR_DB_PATH: str = "./chroma_db"

    # This is the correct Pydantic V2 way to configure settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Create a single, importable instance of the settings
settings = Settings()