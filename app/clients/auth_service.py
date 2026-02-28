import logging
from datetime import datetime
from types import TracebackType
from typing import Any, Self

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
    """Client for Auth Service API.

    Use as an async context manager to share a single HTTP connection pool:

        async with AuthServiceClient() as client:
            await client.create_token(data)
            await client.update_token(token_id, update_data)
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.auth_service_url.rstrip("/")
        self.api_key = settings.auth_service_api_key
        self.timeout = settings.auth_service_timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        accept_statuses: set[int] = frozenset({200}),
        operation: str = "request",
    ) -> httpx.Response:
        """Execute an HTTP request with standard error handling."""
        url = f"{self.base_url}{path}"

        try:
            response = await self._client.request(method, url, json=json, params=params)

            if response.status_code in accept_statuses:
                return response

            if response.status_code == 404 and 404 not in accept_statuses:
                logger.debug("Auth service %s: 404 at %s", operation, url)
                raise AuthServiceError(f"Not found: {path}")

            logger.error(
                "Auth service %s failed: %d - %s", operation, response.status_code, response.text
            )
            raise AuthServiceError(
                f"Failed to {operation}: {response.status_code} - {response.text}"
            )

        except httpx.TimeoutException:
            logger.error("Timeout during auth service %s at %s", operation, url)
            raise AuthServiceError(f"Timeout connecting to Auth Service at {url}") from None
        except httpx.RequestError as e:
            logger.error("Connection error during auth service %s: %s", operation, e)
            raise AuthServiceError(f"Failed to connect to Auth Service: {e}") from e

    async def create_token(self, data: AuthTokenCreate) -> int:
        """Create a token in Auth Service. Returns the auth_token_id."""
        response = await self._request(
            "POST",
            "/api/tokens",
            json=data.model_dump(mode="json", exclude_none=True),
            accept_statuses={200, 201},
            operation=f"create token for {data.user_id}",
        )
        result = response.json()
        logger.info("Created auth token %d for user %s", result["id"], data.user_id)
        return result["id"]

    async def update_token(self, auth_token_id: int, data: AuthTokenUpdate) -> None:
        """Update a token in Auth Service."""
        await self._request(
            "PATCH",
            f"/api/tokens/{auth_token_id}",
            json=data.model_dump(mode="json", exclude_none=True),
            accept_statuses={200, 204},
            operation=f"update token {auth_token_id}",
        )
        logger.info("Updated auth token %d", auth_token_id)

    async def delete_token(self, auth_token_id: int) -> None:
        """Delete a token from Auth Service."""
        await self._request(
            "DELETE",
            f"/api/tokens/{auth_token_id}",
            accept_statuses={200, 204, 404},
            operation=f"delete token {auth_token_id}",
        )
        logger.info("Deleted auth token %d", auth_token_id)

    async def get_user_sessions(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get active sessions for a user from Auth Service."""
        response = await self._request(
            "GET",
            "/api/sessions",
            params={"user_id": user_id, "skip": skip, "limit": limit},
            accept_statuses={200, 404},
            operation=f"get sessions for {user_id}",
        )
        if response.status_code == 404:
            return []
        return response.json()

    async def get_access_logs(
        self,
        *,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query access logs from Auth Service."""
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        if user_id:
            params["user_id"] = user_id
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        response = await self._request(
            "GET",
            "/api/access-logs",
            params=params,
            accept_statuses={200, 404},
            operation="get access logs",
        )
        if response.status_code == 404:
            return []
        return response.json()

    async def get_health(self) -> dict[str, Any]:
        """Get Auth Service health payload."""
        response = await self._request(
            "GET",
            "/health",
            accept_statuses={200},
            operation="get auth health",
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise AuthServiceError("Unexpected Auth health response format")
        return payload

    async def get_stats(self) -> dict[str, Any]:
        """Get Auth Service stats payload."""
        response = await self._request(
            "GET",
            "/stats",
            accept_statuses={200},
            operation="get auth stats",
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise AuthServiceError("Unexpected Auth stats response format")
        return payload

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Fetch normalized Auth Service dashboard stats."""
        health_payload = await self.get_health()

        raw_status = str(health_payload.get("status", "")).strip().lower()
        if raw_status in {"up", "degraded", "down"}:
            health = raw_status
        elif raw_status in {"ok", "healthy", "running"}:
            health = "up"
        else:
            health = "degraded"

        active_tokens: int | None = None
        active_sessions: int | None = None
        error: str | None = None

        try:
            stats_payload = await self.get_stats()
            active_tokens_raw = stats_payload.get("active_tokens")
            active_sessions_raw = stats_payload.get("active_sessions")
            active_tokens = int(active_tokens_raw) if isinstance(active_tokens_raw, int) else None
            active_sessions = int(active_sessions_raw) if isinstance(active_sessions_raw, int) else None
            raw_error = stats_payload.get("error")
            error = str(raw_error) if isinstance(raw_error, str) and raw_error.strip() else None
        except AuthServiceError as e:
            error = str(e)

        return {
            "health": health,
            "active_tokens": active_tokens,
            "active_sessions": active_sessions,
            "error": error,
        }
