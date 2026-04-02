import logging
from typing import Any

import httpx

from app.config import get_settings
from app.exceptions import RutvServiceError

logger = logging.getLogger(__name__)


class RutvClient:
    """Client for RUTV site health and stats endpoints."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.rutv_site_url.rstrip("/")
        self.stats_token = settings.rutv_stats_token
        self.timeout = settings.rutv_site_timeout

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Fetch normalized dashboard stats from RUTV."""
        health_payload = await self.get_health()
        if health_payload.get("ok") is not True:
            raise RutvServiceError("RUTV health check failed")

        health = "up"
        error: str | None = None
        stats_payload: dict[str, Any] = {}

        try:
            stats_payload = await self.get_stats()
        except RutvServiceError as e:
            health = "degraded"
            error = str(e)

        return {
            "health": health,
            "window_seconds": self._as_int(stats_payload.get("window_seconds")),
            "from_at": stats_payload.get("from"),
            "to_at": stats_payload.get("to"),
            "unique_visits": self._as_int(stats_payload.get("unique_visits")),
            "successful_contact_forms": self._as_int(
                stats_payload.get("successful_contact_forms")
            ),
            "error": error,
        }

    async def get_health(self) -> dict[str, Any]:
        """Get RUTV health payload."""
        response = await self._request(
            "GET",
            "/health",
            operation="get RUTV health",
        )

        payload = response.json()
        if not isinstance(payload, dict):
            raise RutvServiceError("Unexpected RUTV health response format")
        return payload

    async def get_stats(self) -> dict[str, Any]:
        """Get RUTV stats payload."""
        response = await self._request(
            "GET",
            "/stats",
            headers={"X-Stats-Token": self.stats_token},
            operation="get RUTV stats",
        )

        payload = response.json()
        if not isinstance(payload, dict):
            raise RutvServiceError("Unexpected RUTV stats response format")
        if payload.get("ok") is not True:
            raise RutvServiceError("RUTV stats request returned ok=false")
        return payload

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        operation: str = "request",
    ) -> httpx.Response:
        """Execute an HTTP request with standard error handling."""
        url = f"{self.base_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers)

            if response.status_code == 200:
                return response

            logger.error(
                "RUTV %s failed: %d - %s",
                operation,
                response.status_code,
                response.text,
            )
            raise RutvServiceError(
                f"Failed to {operation}: {response.status_code}"
            )
        except httpx.TimeoutException:
            logger.error("Timeout during RUTV %s at %s", operation, url)
            raise RutvServiceError(f"Timeout connecting to RUTV at {url}") from None
        except httpx.RequestError as e:
            logger.error("Connection error during RUTV %s: %s", operation, e)
            raise RutvServiceError(f"Failed to connect to RUTV: {e}") from e

    def _as_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return None
        return None
