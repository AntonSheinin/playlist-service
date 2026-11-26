import logging
import sys
from functools import lru_cache

from httpx import InvalidURL, URL
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Time constants (seconds)
SECONDS_PER_DAY = 86400
MINUTES_PER_DAY = 1440


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
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
    integration_api_key: str | None = None

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

    # RuTV Portal Proxy
    portal_base_url: str = ""
    portal_api_key: SecretStr = SecretStr("")
    portal_timeout: float = Field(default=15, gt=0)

    @property
    def portal_configured(self) -> bool:
        return bool(self.portal_base_url.strip() and self.portal_api_key.get_secret_value().strip())

    @field_validator("portal_base_url")
    @classmethod
    def validate_portal_base_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return value

        message = "PORTAL_BASE_URL must be a valid HTTPS URL or use HTTP on host.docker.internal"
        try:
            url = URL(value)
        except InvalidURL:
            raise ValueError(message) from None

        docker_http = url.scheme == "http" and url.host == "host.docker.internal"
        if (
            (url.scheme != "https" and not docker_http)
            or not url.host
            or url.userinfo
            or url.query
            or url.fragment
            or (url.port is not None and not 1 <= url.port <= 65535)
            or any(character.isspace() for character in value)
        ):
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def validate_portal_credentials(self) -> "Settings":
        has_url = bool(self.portal_base_url.strip())
        has_key = bool(self.portal_api_key.get_secret_value().strip())
        if has_url != has_key:
            raise ValueError("Set PORTAL_BASE_URL and PORTAL_API_KEY together")
        return self

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
