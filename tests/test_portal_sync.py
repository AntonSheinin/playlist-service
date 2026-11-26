import json
from contextlib import asynccontextmanager
from functools import partial

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.clients.portal import MAX_PORTAL_BODY_BYTES, PortalClient, PortalSnapshot, encode_snapshot
from app.config import Settings, get_settings
from app.exceptions import PortalSyncError
from app.models import Channel, Package, StreamSource, Tariff
from app.services.user_service import UserService
from scripts import portal_sync
from test_api_contract import _client_with_db
from test_auth_sync import FakeAuthClientContext


class PortalTransport:
    def __init__(self):
        self.requests = []
        self.accounts = {}
        self.status = None
        self.timeout = False

    def __call__(self, request):
        assert request.url.host == "portal.test"
        assert request.headers["X-Internal-Api-Key"] == "portal-test-key"
        self.requests.append(request)
        if self.timeout:
            raise httpx.ReadTimeout("portal-test-key #EXTM3U private body", request=request)
        if self.status is not None:
            return httpx.Response(self.status, text="portal-test-key #EXTM3U private body")
        if request.method == "POST":
            assert request.url.path == "/internal/accounts/upsert"
            assert request.headers["Content-Type"] == "application/json"
            payload = json.loads(request.content)
            assert set(payload) == {
                "account_id", "first_name", "last_name", "portal_allowed", "max_portal_devices", "playlist_m3u"
            }
            metadata = {key: value for key, value in payload.items() if key != "playlist_m3u"}
            metadata.update(created_at="2026-11-26T10:00:00Z", updated_at="2026-11-26T12:00:00+02:00")
            self.accounts[payload["account_id"]] = metadata
            return httpx.Response(200, json=metadata)

        assert request.content == b""
        account_id = int(request.url.path.removeprefix("/internal/accounts/"))
        if request.method == "GET":
            return httpx.Response(200, json=self.accounts[account_id]) if account_id in self.accounts else httpx.Response(404)
        assert request.method == "DELETE"
        self.accounts.pop(account_id, None)
        return httpx.Response(204)

    @property
    def last_snapshot(self):
        return json.loads(self.requests[-1].content)


class RecordingAuth(FakeAuthClientContext):
    async def create_token(self, data):
        await super().create_token(data)
        token_id = 100 + len(self.created)
        self.tokens_by_id[token_id] = {"id": token_id, "token": data.token, "user_id": data.user_id}
        return token_id


@pytest.fixture
def portal(monkeypatch):
    transport = PortalTransport()
    settings = get_settings()
    monkeypatch.setattr(settings, "portal_base_url", "https://portal.test")
    monkeypatch.setattr(settings, "portal_api_key", SecretStr("portal-test-key"))
    monkeypatch.setattr(settings, "flussonic_url", "https://streams.test")
    monkeypatch.setattr(settings, "flussonic_username", "unused")
    monkeypatch.setattr(settings, "flussonic_password", "unused")
    monkeypatch.setattr(
        "app.clients.portal.AsyncClient", partial(httpx.AsyncClient, transport=httpx.MockTransport(transport))
    )
    return transport


@pytest.fixture
def auth(monkeypatch):
    fake = RecordingAuth()
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: fake)
    return fake


def account(**changes):
    return {"first_name": "Alice", "last_name": "Gold", "agreement_number": "100", **changes}


@pytest.mark.parametrize("url, key", [("https://portal.test", ""), (" ", "private-key")])
def test_partial_portal_configuration_is_rejected(url, key):
    with pytest.raises(ValidationError, match="Set PORTAL_BASE_URL and PORTAL_API_KEY together") as error:
        Settings(portal_base_url=url, portal_api_key=key)
    assert "private-key" not in str(error.value)


@pytest.mark.parametrize("url", [
    "http://host.docker.internl:8092",
    "https://portal.test:bad",
    "https://portal.test:65536",
    "https://portal.test?debug=1",
    "https://user:private-password@portal.test",
])
def test_invalid_portal_url_is_rejected_at_startup(url):
    with pytest.raises(ValidationError, match="PORTAL_BASE_URL must be a valid HTTPS URL") as error:
        Settings(portal_base_url=url, portal_api_key="private-key")
    assert "private-key" not in str(error.value)
    assert "private-password" not in str(error.value)


@pytest.mark.asyncio
async def test_portal_is_optional_for_existing_installations(db_session, auth):
    async with _client_with_db(db_session) as api:
        created = await api.post("/api/v1/users", json=account(portal_allowed=True))
        assert created.status_code == 200
        user = created.json()["data"]
        assert user["portal_sync_result"] == "skipped"
        assert user["portal_sync_available"] is False
        assert (await api.post(f"/api/v1/users/{user['id']}/sync-portal")).status_code == 503


@pytest.mark.asyncio
async def test_logo_like_display_title_is_preserved(db_session, portal, auth):
    title = 'News tvg-logo="relative", replay'
    channel = Channel(stream_name="news", display_name=title)
    db_session.add(channel)
    await db_session.commit()

    async with _client_with_db(db_session) as api:
        response = await api.post("/api/v1/users", json=account(portal_allowed=True, channel_ids=[channel.id]))
    assert response.json()["data"]["portal_sync_result"] == "succeeded"
    assert f",{title}\n" in portal.last_snapshot["playlist_m3u"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stream_base, logo", [
    ("https://streams.test:broken", None),
    ("https://streams.test", "https://images.test:65536/news.png"),
])
async def test_portal_rejects_malformed_playlist_ports(db_session, portal, auth, monkeypatch, stream_base, logo):
    monkeypatch.setattr(get_settings(), "flussonic_url", stream_base)
    channel = Channel(stream_name="news", tvg_logo=logo)
    db_session.add(channel)
    await db_session.commit()

    async with _client_with_db(db_session) as api:
        response = await api.post("/api/v1/users", json=account(portal_allowed=True, channel_ids=[channel.id]))
    assert response.status_code == 200
    assert response.json()["data"]["portal_sync_result"] == "failed"
    assert portal.requests == []


@pytest.mark.asyncio
async def test_individual_assignments_update_full_playlist_and_can_remove_last_channel(db_session, portal, auth):
    channel = Channel(source=StreamSource.FLUSSONIC, stream_name="news", tvg_logo="//logos.test/news.png")
    tariff = Tariff(name="News tariff", packages=[Package(name="News", channels=[channel])])
    db_session.add(tariff)
    await db_session.commit()

    async with _client_with_db(db_session) as api:
        created = (await api.post("/api/v1/users", json=account(portal_allowed=True, max_portal_devices=3))).json()["data"]
        path = f"/api/v1/users/{created['id']}"
        assert created["portal_sync_result"] == "succeeded"
        assert portal.last_snapshot["playlist_m3u"] == "#EXTM3U\n"

        assigned = (await api.patch(path, json={"tariff_ids": [tariff.id]})).json()["data"]
        assert assigned["portal_synced"] is True
        playlist = portal.last_snapshot["playlist_m3u"]
        assert 'tvg-logo="http://logos.test/news.png"' in playlist
        assert f"https://streams.test/news/video.m3u8?token={created['token']}" in playlist

        calls = len(portal.requests)
        playback = (await api.patch(path, json={"max_sessions": 5})).json()["data"]
        assert playback["max_portal_devices"] == 3
        assert playback["portal_sync_result"] == "skipped"
        assert len(portal.requests) == calls

        removed = (await api.patch(path, json={"tariff_ids": []})).json()["data"]
        assert removed["portal_synced"] is True
        assert portal.last_snapshot["playlist_m3u"] == "#EXTM3U\n"


@pytest.mark.asyncio
async def test_suspension_manual_resync_and_postcommit_failure(db_session, portal, auth):
    async with _client_with_db(db_session) as api:
        created = (await api.post("/api/v1/users", json=account(portal_allowed=True, max_portal_devices=3))).json()["data"]
        path = f"/api/v1/users/{created['id']}"
        portal.timeout = True
        saved = await api.patch(path, json={"first_name": "Alicia"})
        assert saved.status_code == 200
        assert saved.json()["data"]["first_name"] == "Alicia"
        assert saved.json()["data"]["portal_sync_result"] == "failed"
        assert (await api.get(path)).json()["data"]["portal_synced"] is False
        assert (await api.post(f"{path}/sync-portal")).status_code == 502

        portal.timeout = False
        assert (await api.post(f"{path}/sync-portal")).status_code == 200
        assert portal.last_snapshot["first_name"] == "Alicia"
        saved = await api.patch(path, json={"portal_allowed": False})
        assert saved.json()["data"]["portal_synced"] is True
        assert portal.last_snapshot["max_portal_devices"] == 3
        assert portal.last_snapshot["portal_allowed"] is False
        assert portal.last_snapshot["playlist_m3u"] is None
        assert (await api.patch(path, json={"max_portal_devices": 2})).status_code == 422

        calls = len(portal.requests)
        assert (await api.post(f"{path}/sync-portal")).status_code == 200
        assert len(portal.requests) == calls + 1
        assert portal.last_snapshot["playlist_m3u"] is None

        saved = await api.patch(path, json={"portal_allowed": True})
        assert saved.json()["data"]["portal_synced"] is True
        assert portal.last_snapshot["playlist_m3u"] == "#EXTM3U\n"


@pytest.mark.asyncio
async def test_rotation_publishes_only_a_registered_token(db_session, portal, auth):
    channel = Channel(stream_name="news")
    db_session.add(channel)
    await db_session.commit()
    async with _client_with_db(db_session) as api:
        created = (await api.post("/api/v1/users", json=account(portal_allowed=True, channel_ids=[channel.id]))).json()["data"]
        path = f"/api/v1/users/{created['id']}"
        calls = len(portal.requests)
        auth.fail_create = True
        rotated = (await api.post(f"{path}/regenerate-token")).json()["data"]
        assert rotated["auth_sync_result"] == "failed"
        assert rotated["portal_synced"] is False
        assert (await api.post(f"{path}/sync-portal")).status_code == 502
        assert len(portal.requests) == calls

        auth.fail_create = False
        assert (await api.post(f"{path}/sync-auth")).status_code == 200
        assert (await api.post(f"{path}/sync-portal")).status_code == 200
        assert f"token={rotated['token']}" in portal.last_snapshot["playlist_m3u"]

        rotated = (await api.post(f"{path}/regenerate-token")).json()["data"]
        assert rotated["portal_sync_result"] == "succeeded"
        assert f"token={rotated['token']}" in portal.last_snapshot["playlist_m3u"]


@pytest.mark.asyncio
async def test_portal_delete_can_be_retried_after_auth_revocation(db_session, portal, auth):
    async with _client_with_db(db_session) as api:
        created = (await api.post("/api/v1/users", json=account())).json()["data"]
        path = f"/api/v1/users/{created['id']}"
        portal.status = 503
        assert (await api.delete(path)).status_code == 502
        assert not auth.tokens_by_id
        assert (await api.get(path)).status_code == 200

        portal.status = None
        assert (await api.delete(path)).status_code == 200
        assert (await api.get(path)).status_code == 404
        assert await PortalClient().get(created["id"]) is None


@pytest.mark.asyncio
async def test_backfill_and_size_check_use_existing_accounts(db_session, portal, auth, monkeypatch):
    enabled = await UserService(db_session).create("A", "B", "1", portal_allowed=True)
    enabled.auth_synced = True
    suspended = await UserService(db_session).create("C", "D", "2")
    await db_session.commit()

    @asynccontextmanager
    async def backfill_session():
        yield db_session

    monkeypatch.setattr(portal_sync, "async_session_factory", backfill_session)
    assert await portal_sync.backfill(check_size=True) == 0
    assert portal.requests == []
    for _ in range(2):
        assert await portal_sync.backfill(check_size=False) == 0
    assert len(portal.requests) == 4
    assert portal.last_snapshot["playlist_m3u"] is None
    assert set(portal.accounts) == {enabled.id, suspended.id}
    assert await portal_sync.verify(enabled.id) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 413, 422])
async def test_portal_errors_do_not_expose_response_content(portal, status):
    portal.status = status
    with pytest.raises(PortalSyncError, match=f"Portal returned HTTP {status}") as error:
        await PortalClient().delete(123)
    assert "portal-test-key" not in str(error.value)
    assert "#EXTM3U" not in str(error.value)


@pytest.mark.asyncio
async def test_portal_docker_host_uses_direct_http(monkeypatch):
    def handle(request):
        assert request.url == "http://host.docker.internal:8092/internal/accounts/1"
        assert request.headers["X-Internal-Api-Key"] == "portal-test-key"
        return httpx.Response(404)

    def create_client(**kwargs):
        assert kwargs["trust_env"] is False
        return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(handle))

    settings = Settings(
        portal_base_url="http://host.docker.internal:8092", portal_api_key="portal-test-key"
    )
    monkeypatch.setattr("app.clients.portal.AsyncClient", create_client)
    monkeypatch.setattr("app.clients.portal.get_settings", lambda: settings)
    assert await PortalClient().get(1) is None


def test_portal_body_size_counts_utf8_and_json_escaping():
    snapshot = PortalSnapshot(
        account_id=9_223_372_036_854_775_807, first_name="א", last_name="B",
        portal_allowed=True, max_portal_devices=1, playlist_m3u="#EXTM3U\n",
    )
    body = encode_snapshot(snapshot)
    assert '"first_name":"א"'.encode() in body
    assert b"#EXTM3U\\n" in body
    snapshot.playlist_m3u += "a" * (MAX_PORTAL_BODY_BYTES - len(body))
    assert len(encode_snapshot(snapshot)) == MAX_PORTAL_BODY_BYTES
    snapshot.playlist_m3u += "א"
    with pytest.raises(PortalSyncError, match="8 MiB"):
        encode_snapshot(snapshot)
