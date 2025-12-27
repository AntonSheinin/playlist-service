import logging
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Time constants (seconds)
SECONDS_PER_DAY = 86400
SECONDS_PER_HOUR = 3600
MINUTES_PER_DAY = 1440


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
    session_timeout: int = SECONDS_PER_DAY

    # Flussonic
    flussonic_url: str = "http://localhost:8080"
    flussonic_username: str = "admin"
    flussonic_password: str = ""
    flussonic_timeout: float = 60.0
    flussonic_page_limit: int = 500

    # Auth Service
    auth_service_url: str = "http://localhost:8090"
    auth_service_api_key: str = ""
    auth_service_timeout: float = 30.0

    # Server
    base_url: str = "http://localhost:8080"
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    # Pagination
    pagination_default_per_page: int = 20
    pagination_max_per_page: int = 100
    lookup_default_limit: int = 50
    lookup_max_limit: int = 1000

    # Token
    token_length: int = 32

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging() -> None:
    """Configure application-wide logging with timestamps."""
    settings = get_settings()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Configure uvicorn loggers to use the same format
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = []
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
        uvicorn_logger.addHandler(handler)
        uvicorn_logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.db_echo else logging.WARNING
    )
