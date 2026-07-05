import httpx
import pytest

from app.mcp_server import McpSettings, PlaylistIntegrationClient, create_app, create_mcp


@pytest.mark.asyncio
async def test_mcp_app_rejects_missing_and_invalid_bearer_token():
    app = create_app(
        McpSettings(
            playlist_service_api_url="http://playlist.test",
            playlist_service_api_key="integration-key",
            mcp_auth_token="mcp-secret",
        )
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://mcp.test") as client:
        missing = await client.get("/mcp")
        invalid = await client.get("/mcp", headers={"Authorization": "Bearer wrong"})

    assert missing.status_code == 401
    assert invalid.status_code == 401


@pytest.mark.asyncio
async def test_playlist_integration_client_sends_expected_auth_method_path_and_body(monkeypatch):
    requests = []

    class FakeAsyncClient:
        def __init__(self, *, base_url, headers, timeout):
            self.base_url = base_url
            self.headers = headers
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

        async def request(self, method, path, json=None, params=None):
            requests.append(
                {
                    "base_url": self.base_url,
                    "headers": self.headers,
                    "method": method,
                    "path": path,
                    "json": json,
                    "params": params,
                }
            )
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "user_id": 10,
                        "max_sessions": 3,
                    },
                },
            )

    monkeypatch.setattr("app.mcp_server.httpx.AsyncClient", FakeAsyncClient)
    client = PlaylistIntegrationClient(
        McpSettings(
            playlist_service_api_url="http://playlist.test/",
            playlist_service_api_key="integration-key",
        )
    )

    result = await client.request(
        "PUT",
        "/api/v1/integrations/users/10/max-sessions",
        json={"max_sessions": 3},
    )

    assert result == {"user_id": 10, "max_sessions": 3}
    assert requests == [
        {
            "base_url": "http://playlist.test",
            "headers": {"X-API-Key": "integration-key"},
            "method": "PUT",
            "path": "/api/v1/integrations/users/10/max-sessions",
            "json": {"max_sessions": 3},
            "params": None,
        }
    ]


@pytest.mark.asyncio
async def test_playlist_integration_client_preserves_status_for_non_json_errors(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, *, base_url, headers, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

        async def request(self, method, path, json=None, params=None):
            return httpx.Response(502, text="Bad Gateway")

    monkeypatch.setattr("app.mcp_server.httpx.AsyncClient", FakeAsyncClient)
    client = PlaylistIntegrationClient(
        McpSettings(
            playlist_service_api_url="http://playlist.test/",
            playlist_service_api_key="integration-key",
        )
    )

    with pytest.raises(Exception) as exc_info:
        await client.request("GET", "/api/v1/integrations/users/10")

    assert "502" in str(exc_info.value)


@pytest.mark.asyncio
async def test_playlist_integration_client_preserves_status_for_non_json_success(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, *, base_url, headers, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

        async def request(self, method, path, json=None, params=None):
            return httpx.Response(204, text="")

    monkeypatch.setattr("app.mcp_server.httpx.AsyncClient", FakeAsyncClient)
    client = PlaylistIntegrationClient(
        McpSettings(
            playlist_service_api_url="http://playlist.test/",
            playlist_service_api_key="integration-key",
        )
    )

    with pytest.raises(Exception) as exc_info:
        await client.request("POST", "/api/v1/integrations/users/10/enable")

    assert "204" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mcp_exposes_expected_tools():
    mcp = create_mcp(
        McpSettings(
            playlist_service_api_url="http://playlist.test",
            playlist_service_api_key="integration-key",
            mcp_auth_token="mcp-secret",
        )
    )

    tools = await mcp.list_tools()

    assert {tool.name for tool in tools} == {
        "find_user",
        "get_user",
        "enable_user",
        "disable_user",
        "set_user_max_sessions",
        "set_user_valid_until",
        "get_user_active_sessions",
    }


@pytest.mark.asyncio
async def test_mcp_tool_call_routes_to_playlist_integration_api(monkeypatch):
    requests = []

    class FakeAsyncClient:
        def __init__(self, *, base_url, headers, timeout):
            self.base_url = base_url
            self.headers = headers

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

        async def request(self, method, path, json=None, params=None):
            requests.append(
                {
                    "base_url": self.base_url,
                    "headers": self.headers,
                    "method": method,
                    "path": path,
                    "json": json,
                    "params": params,
                }
            )
            return httpx.Response(
                200,
                json={"success": True, "data": {"user_id": 10}},
            )

    monkeypatch.setattr("app.mcp_server.httpx.AsyncClient", FakeAsyncClient)
    mcp = create_mcp(
        McpSettings(
            playlist_service_api_url="http://playlist.test",
            playlist_service_api_key="integration-key",
        )
    )

    result = await mcp.call_tool("get_user", {"user_id": 10})

    assert result[1] == {"user_id": 10}
    assert requests == [
        {
            "base_url": "http://playlist.test",
            "headers": {"X-API-Key": "integration-key"},
            "method": "GET",
            "path": "/api/v1/integrations/users/10",
            "json": None,
            "params": None,
        }
    ]
