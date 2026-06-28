import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/test")
os.environ.setdefault("DB_POOL_SIZE", "5")
os.environ.setdefault("DB_MAX_OVERFLOW", "10")
os.environ.setdefault("DB_POOL_TIMEOUT", "30")
os.environ.setdefault("DB_ECHO", "false")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SESSION_TIMEOUT", "86400")
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth.test")
os.environ.setdefault("AUTH_SERVICE_API_KEY", "test-key")
os.environ.setdefault("AUTH_SERVICE_TIMEOUT", "30")
os.environ.setdefault("EPG_SERVICE_URL", "http://epg.test")
os.environ.setdefault("EPG_SERVICE_TIMEOUT", "30")
os.environ.setdefault("EPG_SERVICE_FETCH_TIMEOUT", "300")
os.environ.setdefault("RUTV_SITE_URL", "http://rutv.test")
os.environ.setdefault("RUTV_STATS_TOKEN", "test-token")
os.environ.setdefault("RUTV_SITE_TIMEOUT", "30")
os.environ.setdefault("BASE_URL", "http://playlist.test")
os.environ.setdefault("API_HOST", "127.0.0.1")
os.environ.setdefault("API_PORT", "8080")
os.environ.setdefault("PAGINATION_DEFAULT_PER_PAGE", "20")
os.environ.setdefault("PAGINATION_MAX_PER_PAGE", "100")
os.environ.setdefault("LOOKUP_DEFAULT_LIMIT", "50")
os.environ.setdefault("LOOKUP_MAX_LIMIT", "1000")
os.environ.setdefault("TOKEN_LENGTH", "32")
os.environ.setdefault("LOG_LEVEL", "INFO")

from app.dependencies import get_current_admin_id
from app.main import app
from app.models import User, UserStatus
from app.services.database import get_db


async def _override_admin_id() -> int:
    return 1


@asynccontextmanager
async def _client_with_db(db_session) -> AsyncIterator[httpx.AsyncClient]:
    async def override_db():
        yield db_session

    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_admin_id] = _override_admin_id
    app.dependency_overrides[get_db] = override_db
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.mark.asyncio
async def test_representative_success_response_envelope(db_session):
    async with _client_with_db(db_session) as client:
        response = await client.get("/api/v1/lookup/groups")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": []}


@pytest.mark.asyncio
async def test_representative_message_response_envelope(db_session):
    async with _client_with_db(db_session) as client:
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Logged out successfully"}


@pytest.mark.asyncio
async def test_representative_paginated_response_envelope(db_session):
    async with _client_with_db(db_session) as client:
        response = await client.get("/api/v1/channels")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "items": [],
            "total": 0,
            "page": 1,
            "per_page": 20,
            "pages": 1,
        },
    }


class FakeAuthServiceClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def get_user_sessions(self, **kwargs):
        return [
            {
                "started_at": "2026-01-01T10:00:00",
                "client_ip": "127.0.0.1",
                "stream_name": "news",
                "protocol": "hls",
            }
        ]

    async def get_access_logs(self, **kwargs):
        return [
            {
                "timestamp": "2026-01-01T11:00:00",
                "client_ip": "127.0.0.1",
                "stream_name": "news",
                "result": "allowed",
                "protocol": "hls",
            }
        ]


@pytest.mark.asyncio
async def test_sessions_and_access_logs_keep_field_names(db_session, monkeypatch):
    from app.routes import users as users_route

    monkeypatch.setattr(users_route, "AuthServiceClient", FakeAuthServiceClient)
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="300",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
    )
    db_session.add(user)
    await db_session.flush()

    async with _client_with_db(db_session) as client:
        sessions = await client.get(f"/api/v1/users/{user.id}/sessions")
        access_logs = await client.get(f"/api/v1/users/{user.id}/access-logs")

    assert sessions.status_code == 200
    assert set(sessions.json()["data"]["items"][0]) == {
        "started_at",
        "ended_at",
        "duration",
        "ip",
        "channel",
        "user_agent",
    }
    assert access_logs.status_code == 200
    assert set(access_logs.json()["data"]["items"][0]) == {
        "accessed_at",
        "ip",
        "channel",
        "action",
        "user_agent",
    }
