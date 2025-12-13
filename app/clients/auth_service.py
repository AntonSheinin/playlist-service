from datetime import datetime

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import AuthServiceError


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
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/tokens",
                    headers=self._get_headers(),
                    json=data.model_dump(mode="json", exclude_none=True),
                )

                if response.status_code in (200, 201):
                    result = response.json()
                    return result["id"]

                raise AuthServiceError(
                    f"Failed to create token: {response.status_code} - {response.text}"
                )

            except httpx.RequestError as e:
                raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e

    async def update_token(self, auth_token_id: int, data: AuthTokenUpdate) -> None:
        """Update a token in Auth Service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.patch(
                    f"{self.base_url}/api/tokens/{auth_token_id}",
                    headers=self._get_headers(),
                    json=data.model_dump(mode="json", exclude_none=True),
                )

                if response.status_code not in (200, 204):
                    raise AuthServiceError(
                        f"Failed to update token: {response.status_code} - {response.text}"
                    )

            except httpx.RequestError as e:
                raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e

    async def delete_token(self, auth_token_id: int) -> None:
        """Delete a token from Auth Service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/api/tokens/{auth_token_id}",
                    headers=self._get_headers(),
                )

                if response.status_code not in (200, 204, 404):
                    raise AuthServiceError(
                        f"Failed to delete token: {response.status_code} - {response.text}"
                    )

            except httpx.RequestError as e:
                raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e
