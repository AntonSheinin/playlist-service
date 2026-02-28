import logging
from typing import Any

import httpx

from app.config import get_settings
from app.exceptions import EpgServiceError

logger = logging.getLogger(__name__)


class EpgServiceClient:
    """Client for EPG Service API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.epg_service_url.rstrip("/")
        self.timeout = settings.epg_service_timeout
        self.fetch_timeout = settings.epg_service_fetch_timeout

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Fetch normalized dashboard stats from EPG Service."""
        health_payload = await self.get_health()
        stats_payload = await self.get_stats()

        raw_status = str(health_payload.get("status", "")).strip().lower()
        health = raw_status if raw_status in {"up", "degraded", "down"} else "degraded"

        return {
            "health": health,
            "checked_at": stats_payload.get("checked_at"),
            "next_fetch_at": stats_payload.get("next_epg_update_at"),
            "last_epg_update_at": stats_payload.get("last_epg_update_at"),
            "sources_total": stats_payload.get("sources_total"),
            "last_updated_channels_count": stats_payload.get("last_updated_channels_count"),
            "error": stats_payload.get("error"),
        }

    async def trigger_fetch(self) -> dict[str, Any]:
        """Trigger immediate EPG fetch."""
        response = await self._request(
            "POST",
            "/fetch",
            timeout=self.fetch_timeout,
            accept_statuses=frozenset({200, 202}),
            operation="trigger EPG fetch",
        )

        try:
            payload = response.json()
        except ValueError:
            return {"message": "EPG update request accepted"}

        if isinstance(payload, dict):
            return payload
        return {"message": "EPG update request accepted", "result": payload}

    async def get_health(self) -> dict[str, Any]:
        """Get EPG service health payload."""
        response = await self._request(
            "GET",
            "/health",
            operation="get EPG health",
        )

        payload = response.json()
        if not isinstance(payload, dict):
            raise EpgServiceError("Unexpected EPG health response format")
        return payload

    async def get_stats(self) -> dict[str, Any]:
        """Get EPG service stats payload."""
        response = await self._request(
            "GET",
            "/stats",
            accept_statuses=frozenset({200, 500}),
            operation="get EPG stats",
        )

        payload = response.json()
        if not isinstance(payload, dict):
            raise EpgServiceError("Unexpected EPG stats response format")
        return payload

    async def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: float | None = None,
        accept_statuses: frozenset[int] = frozenset({200}),
        operation: str = "request",
    ) -> httpx.Response:
        """Execute an HTTP request with standard error handling."""
        url = f"{self.base_url}{path}"
        request_timeout = timeout if timeout is not None else self.timeout

        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.request(method, url)

            if response.status_code in accept_statuses:
                return response

            logger.error(
                "EPG service %s failed: %d - %s",
                operation,
                response.status_code,
                response.text,
            )
            raise EpgServiceError(
                f"Failed to {operation}: {response.status_code} - {response.text}"
            )

        except httpx.TimeoutException:
            logger.error("Timeout during EPG service %s at %s", operation, url)
            raise EpgServiceError(
                f"Timeout connecting to EPG Service at {url}"
            ) from None
        except httpx.RequestError as e:
            logger.error("Connection error during EPG service %s: %s", operation, e)
            raise EpgServiceError(f"Failed to connect to EPG Service: {e}") from e
