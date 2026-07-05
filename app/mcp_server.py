from __future__ import annotations

import secrets
from typing import Any

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    playlist_service_api_url: str = "http://127.0.0.1:8080"
    playlist_service_api_key: str | None = None
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8091
    mcp_auth_token: str | None = None


class BearerTokenMiddleware:
    def __init__(self, app: ASGIApp, token: str | None) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        expected = f"Bearer {self.token}" if self.token else ""
        if not expected or not secrets.compare_digest(authorization, expected):
            response = JSONResponse(
                {"error": {"code": "UNAUTHORIZED", "message": "Invalid MCP bearer token"}},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class PlaylistIntegrationClient:
    def __init__(self, settings: McpSettings) -> None:
        self.base_url = settings.playlist_service_api_url.rstrip("/")
        self.api_key = settings.playlist_service_api_key

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if not self.api_key:
            raise ToolError("PLAYLIST_SERVICE_API_KEY is not configured")

        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=30.0,
        ) as client:
            try:
                response = await client.request(method, path, json=json, params=params)
            except httpx.RequestError as e:
                raise ToolError(f"Playlist Service request failed: {e}") from e

        if response.is_error:
            payload = self._parse_json_or_none(response)
            message = self._extract_error_message(payload)
            raise ToolError(f"Playlist Service returned {response.status_code}: {message}")

        payload = self._parse_json(response)
        if isinstance(payload, dict) and payload.get("success") is True:
            return payload.get("data", payload.get("message"))
        return payload

    def _parse_json(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as e:
            raise ToolError(
                f"Playlist Service returned {response.status_code} with non-JSON response"
            ) from e

    def _parse_json_or_none(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    def _extract_error_message(self, payload: Any) -> str:
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                return str(error["message"])
            detail = payload.get("detail")
            if isinstance(detail, dict) and detail.get("message"):
                return str(detail["message"])
            if isinstance(detail, str):
                return detail
        return "Unexpected error"


def create_mcp(settings: McpSettings | None = None) -> FastMCP:
    settings = settings or McpSettings()
    client = PlaylistIntegrationClient(settings)
    mcp = FastMCP(
        "Playlist Service",
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path="/mcp",
        json_response=True,
    )

    @mcp.tool()
    async def find_user(q: str) -> dict[str, Any]:
        """Find a user by exact agreement number, first name, last name, or full name."""
        return await client.request(
            "GET",
            "/api/v1/integrations/users/find",
            params={"q": q},
        )

    @mcp.tool()
    async def get_user(user_id: int) -> dict[str, Any]:
        """Get compact integration user details."""
        return await client.request("GET", f"/api/v1/integrations/users/{user_id}")

    @mcp.tool()
    async def enable_user(user_id: int) -> dict[str, Any]:
        """Enable a user and strictly sync Auth Backend."""
        return await client.request("POST", f"/api/v1/integrations/users/{user_id}/enable")

    @mcp.tool()
    async def disable_user(user_id: int) -> dict[str, Any]:
        """Disable a user and strictly sync Auth Backend."""
        return await client.request("POST", f"/api/v1/integrations/users/{user_id}/disable")

    @mcp.tool()
    async def set_user_max_sessions(user_id: int, max_sessions: int) -> dict[str, Any]:
        """Set a user's exact simultaneous session count."""
        return await client.request(
            "PUT",
            f"/api/v1/integrations/users/{user_id}/max-sessions",
            json={"max_sessions": max_sessions},
        )

    @mcp.tool()
    async def set_user_valid_until(user_id: int, valid_until: str) -> dict[str, Any]:
        """Set a user's valid_until datetime. The value must include timezone information."""
        return await client.request(
            "PUT",
            f"/api/v1/integrations/users/{user_id}/valid-until",
            json={"valid_until": valid_until},
        )

    @mcp.tool()
    async def get_user_active_sessions(user_id: int) -> list[dict[str, Any]]:
        """Get currently active sessions for a user."""
        return await client.request("GET", f"/api/v1/integrations/users/{user_id}/sessions")

    return mcp


def create_app(settings: McpSettings | None = None) -> ASGIApp:
    settings = settings or McpSettings()
    mcp = create_mcp(settings)
    return BearerTokenMiddleware(mcp.streamable_http_app(), settings.mcp_auth_token)


app = create_app()


def main() -> None:
    settings = McpSettings()
    uvicorn.run(create_app(settings), host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
    main()
