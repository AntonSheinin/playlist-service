import logging
from datetime import datetime

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import AuthServiceError

logger = logging.getLogger(__name__)


class AuthTokenCreate(BaseModel):
    """Request payload for creating a token in Auth Service."""

    token: str
    user_id: str  # agreement_number
    status: str  # "active" or "suspended"
    max_sessions: int
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    allowed_streams: list[str]
    meta: dict[str, str] | None = None


class AuthTokenUpdate(BaseModel):
    """Request payload for updating a token in Auth Service."""

    status: str | None = None
    max_sessions: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    allowed_streams: list[str] | None = None
    meta: dict[str, str] | None = None


class AuthServiceClient:
    """Client for Auth Service API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.auth_service_url.rstrip("/")
        self.api_key = settings.auth_service_api_key
        self.timeout = settings.auth_service_timeout

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_token(self, data: AuthTokenCreate) -> int:
        """
        Create a token in Auth Service.
        Returns the auth_token_id from the response.
        """
        url = f"{self.base_url}/api/tokens"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=data.model_dump(mode="json", exclude_none=True),
                )

                if response.status_code in (200, 201):
                    result = response.json()
                    logger.info("Created auth token %d for user %s", result["id"], data.user_id)
                    return result["id"]

                logger.error(
                    "Failed to create auth token for %s: %d - %s",
                    data.user_id, response.status_code, response.text
                )
                raise AuthServiceError(
                    f"Failed to create token: {response.status_code} - {response.text}"
                )

            except httpx.TimeoutException:
                logger.error("Timeout creating auth token for %s at %s", data.user_id, url)
                raise AuthServiceError(f"Timeout connecting to Auth Service at {url}") from None
            except httpx.RequestError as e:
                logger.error("Connection error creating auth token: %s", e)
                raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e

    async def update_token(self, auth_token_id: int, data: AuthTokenUpdate) -> None:
        """Update a token in Auth Service."""
        url = f"{self.base_url}/api/tokens/{auth_token_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.patch(
                    url,
                    headers=self._get_headers(),
                    json=data.model_dump(mode="json", exclude_none=True),
                )

                if response.status_code in (200, 204):
                    logger.info("Updated auth token %d", auth_token_id)
                    return

                logger.error(
                    "Failed to update auth token %d: %d - %s",
                    auth_token_id, response.status_code, response.text
                )
                raise AuthServiceError(
                    f"Failed to update token: {response.status_code} - {response.text}"
                )

            except httpx.TimeoutException:
                logger.error("Timeout updating auth token %d at %s", auth_token_id, url)
                raise AuthServiceError(f"Timeout connecting to Auth Service at {url}") from None
            except httpx.RequestError as e:
                logger.error("Connection error updating auth token %d: %s", auth_token_id, e)
                raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e

    async def delete_token(self, auth_token_id: int) -> None:
        """Delete a token from Auth Service."""
        url = f"{self.base_url}/api/tokens/{auth_token_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.delete(url, headers=self._get_headers())

                if response.status_code in (200, 204, 404):
                    logger.info("Deleted auth token %d", auth_token_id)
                    return

                logger.error(
                    "Failed to delete auth token %d: %d - %s",
                    auth_token_id, response.status_code, response.text
                )
                raise AuthServiceError(
                    f"Failed to delete token: {response.status_code} - {response.text}"
                )

            except httpx.TimeoutException:
                logger.error("Timeout deleting auth token %d at %s", auth_token_id, url)
                raise AuthServiceError(f"Timeout connecting to Auth Service at {url}") from None
            except httpx.RequestError as e:
                logger.error("Connection error deleting auth token %d: %s", auth_token_id, e)
                raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e
