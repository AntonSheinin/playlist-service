import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.clients.stream_provider import ProviderDashboardStats, ProviderStream
from app.config import get_settings
from app.exceptions import NimbleError
from app.models import StreamSource

logger = logging.getLogger(__name__)

SERVER_ENDPOINT_TEMPLATE = "/v1/server/{server_id}"
LIVE_STREAMS_ENDPOINT_TEMPLATE = "/v1/server/{server_id}/live/streams"
HEALTH_UP_VALUES = {"up", "ok", "online", "running", "active", "enabled", "connected"}
HEALTH_DOWN_VALUES = {"down", "offline", "error", "failed", "inactive", "disabled", "disconnected"}
HEALTH_DEGRADED_VALUES = {"degraded", "warning", "pending", "initializing", "starting"}
BROKEN_STREAM_VALUES = {
    "error",
    "failed",
    "broken",
    "offline",
    "stopped",
    "paused",
    "inactive",
    "disconnected",
}


class NimbleClient:
    """Client for Nimble data exposed through the WMSPanel API."""

    source = StreamSource.NIMBLE

    def __init__(self) -> None:
        settings = get_settings()
        if (
            not settings.wmspanel_api_url
            or not settings.wmspanel_client_id
            or not settings.wmspanel_api_key
            or not settings.wmspanel_server_id
            or not settings.nimble_playback_url
        ):
            raise NimbleError("Not configured")

        self.base_url = settings.wmspanel_api_url.rstrip("/")
        self.client_id = settings.wmspanel_client_id
        self.api_key = settings.wmspanel_api_key
        self.server_id = settings.wmspanel_server_id
        self.timeout = settings.nimble_timeout
        self.playback_url = settings.nimble_playback_url.rstrip("/")
        self.application = settings.nimble_application.strip("/")
        self.playlist_path = settings.nimble_playlist_path.lstrip("/")
        self.token_query_param = settings.nimble_token_query_param

    def build_stream_url(self, stream_name: str, token: str) -> str:
        query = urlencode({self.token_query_param: token})
        return f"{self.playback_url}/{self.application}/{stream_name}/{self.playlist_path}?{query}"

    async def get_streams(self) -> list[ProviderStream]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = await self._get_json(
                client,
                LIVE_STREAMS_ENDPOINT_TEMPLATE.format(server_id=self.server_id),
                "get Nimble streams from WMSPanel",
            )

        streams: list[ProviderStream] = []
        for item in self._iter_application_streams(payload):
            name = self._get_first_string(item, "stream", "name", "stream_name")
            if not name:
                continue
            title = self._get_first_string(item, "description", "title") or name
            streams.append(
                ProviderStream(
                    name=name,
                    title=title,
                    catchup_days=self._as_int(
                        self._get_first_value(item, "catchup_days", "dvr_days", "archive_days")
                    ),
                )
            )

        logger.info(
            "Fetched %d streams from Nimble application %s through WMSPanel server %s",
            len(streams),
            self.application,
            self.server_id,
        )
        return streams

    async def get_dashboard_stats(self) -> ProviderDashboardStats:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            server_payload = await self._get_json(
                client,
                SERVER_ENDPOINT_TEMPLATE.format(server_id=self.server_id),
                "get Nimble server details from WMSPanel",
            )
            streams_payload = await self._get_json(
                client,
                LIVE_STREAMS_ENDPOINT_TEMPLATE.format(server_id=self.server_id),
                "get Nimble live streams from WMSPanel",
            )

        server = self._extract_server_payload(server_payload)
        application_streams = list(self._iter_application_streams(streams_payload))
        total_sources = len(application_streams)
        broken_sources = sum(1 for item in application_streams if self._is_broken_stream(item))
        good_sources = max(total_sources - broken_sources, 0)

        return ProviderDashboardStats(
            health=self._derive_health(server),
            incoming_kbit=self._find_first_int(
                server,
                "incoming_kbit",
                "input_kbit",
                "in_kbit",
                "ingress_kbit",
            ),
            outgoing_kbit=self._find_first_int(
                server,
                "outgoing_kbit",
                "output_kbit",
                "out_kbit",
                "egress_kbit",
            ),
            total_clients=self._find_first_int(
                server,
                "total_clients",
                "clients",
                "viewers",
                "active_clients",
            ),
            total_sources=total_sources,
            good_sources=good_sources,
            broken_sources=broken_sources,
        )

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        operation: str,
    ) -> Any:
        url = f"{self.base_url}{path}"

        try:
            response = await client.get(url, params=self._build_auth_params())
            if response.status_code != 200:
                raise NimbleError(f"Failed to {operation}: {response.status_code}")

            payload = response.json()
            if isinstance(payload, dict):
                status = payload.get("status")
                if isinstance(status, str) and status.lower() in {"error", "fail", "failed"}:
                    message = self._extract_error_message(payload)
                    raise NimbleError(message or f"Failed to {operation}")
            return payload
        except ValueError as e:
            raise NimbleError(f"Failed to decode WMSPanel response during {operation}: {e}") from e
        except httpx.TimeoutException:
            raise NimbleError(f"Timeout during {operation} at {url}") from None
        except httpx.RequestError as e:
            raise NimbleError(f"Failed to connect to WMSPanel during {operation}: {e}") from e

    def _build_auth_params(self) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "api_key": self.api_key,
        }

    def _extract_server_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise NimbleError("Unexpected WMSPanel server response format")

        server = payload.get("server")
        if isinstance(server, dict):
            return server
        return payload

    def _extract_stream_items(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise NimbleError("Unexpected WMSPanel live streams response format")

        for key in ("streams", "live_streams", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        raise NimbleError("Unexpected WMSPanel live streams response format")

    def _iter_application_streams(self, payload: Any) -> list[dict[str, Any]]:
        items = self._extract_stream_items(payload)
        return [
            item
            for item in items
            if self._get_first_string(item, "application", "app", "app_name") == self.application
        ]

    def _is_broken_stream(self, item: dict[str, Any]) -> bool:
        status = self._get_first_string(item, "status", "state", "stream_status")
        if not status:
            return False
        return status.strip().lower() in BROKEN_STREAM_VALUES

    def _derive_health(self, server: dict[str, Any]) -> str:
        for key in ("online", "is_online", "connected", "is_active"):
            value = server.get(key)
            if isinstance(value, bool):
                return "up" if value else "down"

        status = self._get_first_string(server, "server_status", "health", "status", "state")
        if status:
            normalized = status.strip().lower()
            if normalized in HEALTH_UP_VALUES:
                return "up"
            if normalized in HEALTH_DOWN_VALUES:
                return "down"
            if normalized in HEALTH_DEGRADED_VALUES:
                return "degraded"

        return "up"

    def _extract_error_message(self, payload: dict[str, Any]) -> str | None:
        return self._get_first_string(payload, "message", "error", "description")

    def _get_first_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in payload:
                return payload[key]
        return None

    def _get_first_string(self, payload: dict[str, Any], *keys: str) -> str | None:
        value = self._get_first_value(payload, *keys)
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    def _find_first_int(self, payload: Any, *keys: str) -> int | None:
        if isinstance(payload, dict):
            for key in keys:
                if key in payload:
                    value = self._as_int(payload[key])
                    if value is not None:
                        return value

            for value in payload.values():
                found = self._find_first_int(value, *keys)
                if found is not None:
                    return found

        if isinstance(payload, list):
            for item in payload:
                found = self._find_first_int(item, *keys)
                if found is not None:
                    return found

        return None

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
