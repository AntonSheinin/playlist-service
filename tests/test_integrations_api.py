import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

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
os.environ.setdefault("INTEGRATION_API_KEY", "integration-test-key")

from app.config import get_settings
from app.main import app
from app.models import User, UserStatus
from app.services.database import get_db


class RecordingStrictAuthSyncService:
    calls: list[dict] = []
    fail = False

    def __init__(self, db):
        self.db = db

    async def sync_user_update(self, user, *, recreate_token=False, strict=False):
        self.calls.append(
            {
                "user_id": user.id,
                "status": user.status,
                "max_sessions": user.max_sessions,
                "valid_until": user.valid_until,
                "recreate_token": recreate_token,
                "strict": strict,
            }
        )
        if self.fail:
            from app.exceptions import AuthServiceError

            raise AuthServiceError("sync failed")


class FakeAuthServiceClient:
    calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def get_user_sessions(self, **kwargs):
        self.calls.append(kwargs)
        return [
            {
                "started_at": "2026-01-01T10:00:00",
                "client_ip": "127.0.0.1",
                "stream_name": "news",
                "protocol": "hls",
            }
        ]


@asynccontextmanager
async def _client_with_db(db_session) -> AsyncIterator[httpx.AsyncClient]:
    async def override_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    previous_overrides = dict(app.dependency_overrides)
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = override_db
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        get_settings.cache_clear()


def _headers() -> dict[str, str]:
    return {"X-API-Key": "integration-test-key"}


async def _create_user(
    db_session,
    *,
    first_name="Alice",
    last_name="Smith",
    agreement_number="AG12345",
    status=UserStatus.ENABLED,
    max_sessions=1,
    valid_until=None,
    token="token",
) -> User:
    user = User(
        first_name=first_name,
        last_name=last_name,
        agreement_number=agreement_number,
        status=status,
        max_sessions=max_sessions,
        valid_until=valid_until,
        token=token,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_integration_api_rejects_missing_and_invalid_key(db_session):
    async with _client_with_db(db_session) as client:
        missing = await client.get("/api/v1/integrations/users/find?q=AG123")
        invalid = await client.get(
            "/api/v1/integrations/users/find?q=AG123",
            headers={"X-API-Key": "wrong"},
        )

    assert missing.status_code == 401
    assert invalid.status_code == 401


@pytest.mark.asyncio
async def test_integration_api_rejects_when_key_is_not_configured(db_session, monkeypatch):
    monkeypatch.delenv("INTEGRATION_API_KEY", raising=False)

    async with _client_with_db(db_session) as client:
        response = await client.get(
            "/api/v1/integrations/users/find?q=AG123",
            headers=_headers(),
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_find_user_exact_matches_and_candidates(db_session):
    user = await _create_user(db_session)
    other = await _create_user(
        db_session,
        first_name="Bob",
        last_name="Smith",
        agreement_number="AG54321",
        token="token-2",
    )
    user_id = user.id
    other_id = other.id

    async with _client_with_db(db_session) as client:
        by_agreement = await client.get(
            "/api/v1/integrations/users/find?q=AG12345",
            headers=_headers(),
        )
        by_lower_agreement = await client.get(
            "/api/v1/integrations/users/find?q=ag12345",
            headers=_headers(),
        )
        by_full_name = await client.get(
            "/api/v1/integrations/users/find?q=smith alice",
            headers=_headers(),
        )
        by_spaced_full_name = await client.get(
            "/api/v1/integrations/users/find?q=%20%20smith%20alice%20%20",
            headers=_headers(),
        )
        by_first_name = await client.get(
            "/api/v1/integrations/users/find?q=alice",
            headers=_headers(),
        )
        by_collapsed_query = await client.get(
            "/api/v1/integrations/users/find?q=smith%20%20alice",
            headers=_headers(),
        )
        by_last_name = await client.get(
            "/api/v1/integrations/users/find?q=smith",
            headers=_headers(),
        )
        partial = await client.get(
            "/api/v1/integrations/users/find?q=AG12",
            headers=_headers(),
        )

    assert by_agreement.json()["data"]["match_type"] == "single"
    assert by_agreement.json()["data"]["user"]["user_id"] == user_id
    assert by_lower_agreement.json()["data"]["user"]["user_id"] == user_id
    assert by_full_name.json()["data"]["user"]["user_id"] == user_id
    assert by_spaced_full_name.json()["data"]["user"]["user_id"] == user_id
    assert by_first_name.json()["data"]["user"]["user_id"] == user_id
    assert by_last_name.json()["data"]["match_type"] == "candidates"
    assert [item["user_id"] for item in by_last_name.json()["data"]["candidates"]] == [
        user_id,
        other_id,
    ]
    assert by_collapsed_query.status_code == 404
    assert partial.status_code == 404


@pytest.mark.asyncio
async def test_find_user_rejects_too_short_query(db_session):
    async with _client_with_db(db_session) as client:
        response = await client.get("/api/v1/integrations/users/find?q=a", headers=_headers())

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_user_returns_compact_integration_summary(db_session):
    user = await _create_user(db_session, valid_until=datetime(2026, 1, 1, tzinfo=timezone.utc))

    async with _client_with_db(db_session) as client:
        response = await client.get(f"/api/v1/integrations/users/{user.id}", headers=_headers())

    assert response.status_code == 200
    assert response.json()["data"] == {
        "user_id": user.id,
        "first_name": "Alice",
        "last_name": "Smith",
        "agreement_number": "AG12345",
        "status": "enabled",
        "max_sessions": 1,
        "valid_until": response.json()["data"]["valid_until"],
    }


@pytest.mark.asyncio
async def test_enable_disable_and_max_sessions_call_strict_auth_sync(db_session, monkeypatch):
    from app.routes import integrations as integrations_route

    RecordingStrictAuthSyncService.calls = []
    RecordingStrictAuthSyncService.fail = False
    monkeypatch.setattr(integrations_route, "AuthSyncService", RecordingStrictAuthSyncService)
    user = await _create_user(db_session, status=UserStatus.DISABLED)

    async with _client_with_db(db_session) as client:
        enabled = await client.post(
            f"/api/v1/integrations/users/{user.id}/enable",
            headers=_headers(),
        )
        sessions = await client.put(
            f"/api/v1/integrations/users/{user.id}/max-sessions",
            json={"max_sessions": 3},
            headers=_headers(),
        )
        disabled = await client.post(
            f"/api/v1/integrations/users/{user.id}/disable",
            headers=_headers(),
        )

    assert enabled.status_code == 200
    assert enabled.json()["data"]["status"] == "enabled"
    assert sessions.status_code == 200
    assert sessions.json()["data"]["max_sessions"] == 3
    assert disabled.status_code == 200
    assert disabled.json()["data"]["status"] == "disabled"
    assert [call["strict"] for call in RecordingStrictAuthSyncService.calls] == [True, True, True]


@pytest.mark.asyncio
async def test_invalid_max_sessions_is_rejected_before_auth_sync(db_session, monkeypatch):
    from app.routes import integrations as integrations_route

    RecordingStrictAuthSyncService.calls = []
    RecordingStrictAuthSyncService.fail = False
    monkeypatch.setattr(integrations_route, "AuthSyncService", RecordingStrictAuthSyncService)
    user = await _create_user(db_session)

    async with _client_with_db(db_session) as client:
        response = await client.put(
            f"/api/v1/integrations/users/{user.id}/max-sessions",
            json={"max_sessions": 0},
            headers=_headers(),
        )

    assert response.status_code == 422
    assert RecordingStrictAuthSyncService.calls == []


@pytest.mark.asyncio
async def test_valid_until_requires_timezone_and_calls_strict_auth_sync(db_session, monkeypatch):
    from app.routes import integrations as integrations_route

    RecordingStrictAuthSyncService.calls = []
    RecordingStrictAuthSyncService.fail = False
    monkeypatch.setattr(integrations_route, "AuthSyncService", RecordingStrictAuthSyncService)
    user = await _create_user(db_session)

    async with _client_with_db(db_session) as client:
        naive = await client.put(
            f"/api/v1/integrations/users/{user.id}/valid-until",
            json={"valid_until": "2026-12-31T23:59:59"},
            headers=_headers(),
        )
        aware = await client.put(
            f"/api/v1/integrations/users/{user.id}/valid-until",
            json={"valid_until": "2026-12-31T23:59:59+02:00"},
            headers=_headers(),
        )

    assert naive.status_code == 422
    assert aware.status_code == 200
    assert aware.json()["data"]["valid_until"].startswith("2026-12-31T21:59:59")
    assert RecordingStrictAuthSyncService.calls[-1]["strict"] is True
    assert RecordingStrictAuthSyncService.calls[-1]["valid_until"] == datetime(
        2026, 12, 31, 21, 59, 59
    )
    await db_session.refresh(user)
    assert user.valid_until == datetime(2026, 12, 31, 21, 59, 59)


@pytest.mark.asyncio
async def test_auth_sync_failure_rolls_back_local_user_change(db_session, monkeypatch):
    from app.routes import integrations as integrations_route

    RecordingStrictAuthSyncService.calls = []
    RecordingStrictAuthSyncService.fail = True
    monkeypatch.setattr(integrations_route, "AuthSyncService", RecordingStrictAuthSyncService)
    user = await _create_user(db_session, status=UserStatus.ENABLED)

    async with _client_with_db(db_session) as client:
        response = await client.post(
            f"/api/v1/integrations/users/{user.id}/disable",
            headers=_headers(),
        )

    await db_session.refresh(user)
    assert response.status_code == 502
    assert user.status == UserStatus.ENABLED
    assert RecordingStrictAuthSyncService.calls[0]["strict"] is True


@pytest.mark.asyncio
async def test_active_sessions_use_existing_mapping(db_session, monkeypatch):
    from app.routes import integrations as integrations_route

    FakeAuthServiceClient.calls = []
    monkeypatch.setattr(integrations_route, "AuthServiceClient", FakeAuthServiceClient)
    user = await _create_user(db_session)

    async with _client_with_db(db_session) as client:
        response = await client.get(
            f"/api/v1/integrations/users/{user.id}/sessions",
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["data"][0] == {
        "started_at": "2026-01-01T10:00:00",
        "ended_at": None,
        "duration": response.json()["data"][0]["duration"],
        "ip": "127.0.0.1",
        "channel": "news",
        "user_agent": "hls",
    }
    assert FakeAuthServiceClient.calls == [{"user_id": str(user.id), "skip": 0, "limit": 100}]
