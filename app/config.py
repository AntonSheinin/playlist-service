import logging
import sys
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Time constants (seconds)
SECONDS_PER_DAY = 86400
MINUTES_PER_DAY = 1440


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(min_length=1)

    @property
    def async_database_url(self) -> str:
        """Convert standard postgresql:// URL to async driver format."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout: int
    db_echo: bool

    # Security
    secret_key: str = Field(min_length=1)
    session_timeout: int

    # Flussonic
    flussonic_url: str | None = None
    flussonic_username: str | None = None
    flussonic_password: str | None = None
    flussonic_timeout: float = 60
    flussonic_page_limit: int = 500

    # Nimble via WMSPanel
    wmspanel_api_url: str | None = None
    wmspanel_client_id: str | None = None
    wmspanel_api_key: str | None = None
    wmspanel_server_id: str | None = None
    nimble_timeout: float = 30
    nimble_playback_url: str | None = None
    nimble_application: str = "live"
    nimble_playlist_path: str = "playlist.m3u8"
    nimble_token_query_param: str = "token"

    # Auth Service
    auth_service_url: str = Field(min_length=1)
    auth_service_api_key: str = Field(min_length=1)
    auth_service_timeout: float

    # EPG Service
    epg_service_url: str = Field(min_length=1)
    epg_service_timeout: float
    epg_service_fetch_timeout: float

    # RUTV Site
    rutv_site_url: str = Field(min_length=1)
    rutv_stats_token: str = Field(min_length=1)
    rutv_site_timeout: float

    # Server
    base_url: str = Field(min_length=1)
    api_host: str = Field(min_length=1)
    api_port: int

    # Pagination
    pagination_default_per_page: int
    pagination_max_per_page: int
    lookup_default_limit: int
    lookup_max_limit: int

    # Token
    token_length: int

    # Logging
    log_level: str = Field(min_length=1)


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
