from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/playlist_service"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_echo: bool = False

    # Security
    secret_key: str = "change-me-in-production"
    session_timeout: int = 86400  # 24 hours in seconds

    # Flussonic
    flussonic_url: str = "http://localhost:8080"
    flussonic_username: str = "admin"
    flussonic_password: str = ""

    # Auth Service
    auth_service_url: str = "http://localhost:8090"
    auth_service_api_key: str = ""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8080


@lru_cache
def get_settings() -> Settings:
    return Settings()
