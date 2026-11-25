import pytest

from app.config import get_settings
from app.exceptions import AuthServiceError
from app.models import Channel, Package, StreamSource
from app.services.user_service import UserService
from test_api_contract import _client_with_db
from test_auth_sync import FakeAuthClientContext


@pytest.mark.asyncio
async def test_admin_save_can_retry_auth_independently_of_portal(db_session, monkeypatch):
    fake = FakeAuthClientContext(fail_create=True)
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: fake)
    monkeypatch.setattr(get_settings(), "app_environment", "test")
    monkeypatch.setattr(get_settings(), "portal_sync_mock", None)
    async with _client_with_db(db_session) as client:
        created = await client.post("/api/v1/users", json={
            "first_name": "Alice", "last_name": "Smith", "agreement_number": "AG01",
            "portal_allowed": True,
        })
        assert created.status_code == 200
        user = created.json()["data"]
        assert user["auth_sync_result"] == "failed"
        assert user["auth_synced"] is False
        assert user["portal_synced"] is False
        assert "auth_previous_token" not in user
        path = f"/api/v1/users/{user['id']}"

        failed = await client.post(f"{path}/sync-auth")
        assert failed.status_code == 502
        unavailable = await client.post(f"{path}/sync-portal")
        assert unavailable.status_code == 503

        monkeypatch.setattr(get_settings(), "portal_sync_mock", "failure")
        failed_portal = await client.post(f"{path}/sync-portal")
        assert failed_portal.status_code == 502

        fake.fail_create = False
        synced = await client.post(f"{path}/sync-auth")
        assert synced.status_code == 200
        assert synced.json()["data"]["auth_synced"] is True
        assert synced.json()["data"]["portal_synced"] is False

        monkeypatch.setattr(get_settings(), "portal_sync_mock", "success")
        portal_synced = await client.post(f"{path}/sync-portal")
        assert portal_synced.status_code == 200
        assert portal_synced.json()["data"]["portal_synced"] is True

        edited = await client.patch(path, json={"first_name": "Alicia"})
        assert edited.json()["data"]["auth_sync_result"] == "skipped"
        listed = (await client.get("/api/v1/users")).json()["data"]["items"]
        assert listed[0]["auth_synced"] is True
        assert listed[0]["portal_synced"] is True
        assert listed[0]["portal_sync_available"] is True

        monkeypatch.setattr(get_settings(), "app_environment", "production")
        disabled = await client.post(f"{path}/sync-portal")
        assert disabled.status_code == 503
        detail = (await client.get(path)).json()["data"]
        listed = (await client.get("/api/v1/users")).json()["data"]["items"]
        for view in (detail, listed[0]):
            assert view["portal_sync_available"] is False
            assert view["portal_synced"] is False
    assert len(fake.created) == 1


@pytest.mark.asyncio
async def test_portal_device_limit_and_sync_follow_saved_portal_access(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "app_environment", "test")
    monkeypatch.setattr(settings, "portal_sync_mock", "success")
    fake = FakeAuthClientContext()
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: fake)

    async with _client_with_db(db_session) as client:
        account = {"first_name": "Alice", "last_name": "Smith", "agreement_number": "AG02"}
        denied_create = await client.post("/api/v1/users", json={**account, "max_portal_devices": 3})
        assert denied_create.status_code == 422
        created = await client.post("/api/v1/users", json=account)
        assert created.status_code == 200
        data = created.json()["data"]
        path = f"/api/v1/users/{data['id']}"
        assert data["max_portal_devices"] == 1
        assert data["portal_sync_available"] is False
        assert (await client.post(f"{path}/sync-portal")).status_code == 422
        assert (await client.patch(path, json={"max_portal_devices": 2})).status_code == 422

        enabled = await client.patch(path, json={"portal_allowed": True, "max_portal_devices": 3})
        assert enabled.status_code == 200
        assert enabled.json()["data"]["max_portal_devices"] == 3
        assert enabled.json()["data"]["portal_sync_available"] is True
        assert (await client.patch(path, json={"max_portal_devices": 0})).status_code == 422
        synced = await client.post(f"{path}/sync-portal")
        assert synced.json()["data"]["portal_synced"] is True

        unchanged = await client.patch(path, json={"max_portal_devices": 3})
        assert unchanged.json()["data"]["portal_synced"] is True
        changed = await client.patch(path, json={"max_portal_devices": 4})
        assert changed.json()["data"]["portal_synced"] is False
        assert changed.json()["data"]["auth_synced"] is True
        await client.post(f"{path}/sync-portal")

        disabled = await client.patch(path, json={"portal_allowed": False})
        assert disabled.json()["data"]["max_portal_devices"] == 4
        assert disabled.json()["data"]["portal_synced"] is False
        assert disabled.json()["data"]["portal_sync_available"] is False
        listed = (await client.get("/api/v1/users")).json()["data"]["items"][0]
        assert listed["portal_synced"] is False
        assert listed["portal_sync_available"] is False
        reenabled = await client.patch(path, json={"portal_allowed": True})
        assert reenabled.json()["data"]["max_portal_devices"] == 4
        assert reenabled.json()["data"]["portal_synced"] is False
    assert len(fake.created) == 1
    assert not fake.updated


@pytest.mark.asyncio
async def test_force_delete_channel_syncs_only_changed_stream_sets(db_session, monkeypatch):
    removed = Channel(source=StreamSource.FLUSSONIC, stream_name="news")
    alternative = Channel(source=StreamSource.NIMBLE, stream_name="news")
    package = Package(name="News", channels=[removed])
    db_session.add_all([package, alternative])
    await db_session.flush()
    losing_access = await UserService(db_session).create("A", "B", "1", package_ids=[package.id])
    retaining_access = await UserService(db_session).create(
        "C", "D", "2", channel_ids=[removed.id, alternative.id]
    )
    fake = FakeAuthClientContext()
    for token_id, user in enumerate([losing_access, retaining_access], start=10):
        user.auth_synced = True
        user.auth_token_id = token_id
        fake.tokens_by_id[token_id] = {"id": token_id, "token": user.token, "user_id": str(user.id)}
    await db_session.commit()
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: fake)

    async with _client_with_db(db_session) as client:
        response = await client.delete(f"/api/v1/channels/{removed.id}?force=true")
    assert response.status_code == 200
    assert [(token_id, payload.allowed_streams) for token_id, payload in fake.updated] == [(10, [])]
    assert losing_access.auth_synced is True
    assert retaining_access.auth_synced is True


@pytest.mark.asyncio
async def test_token_rotation_retry_revokes_previous_token_without_deleting_stale_id(
    db_session, monkeypatch,
):
    class RotationClient(FakeAuthClientContext):
        fail_delete = True

        async def delete_token(self, token_id):
            if self.fail_delete:
                raise AuthServiceError("Auth unavailable")
            await super().delete_token(token_id)

    user = await UserService(db_session).create("A", "B", "1")
    user.auth_token_id = 10
    old_token = user.token
    client_auth = RotationClient()
    client_auth.tokens_by_id = {
        10: {"id": 10, "token": "unrelated", "user_id": "another-account"},
        20: {"id": 20, "token": old_token, "user_id": str(user.id)},
    }
    await db_session.commit()
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client_auth)
    path = f"/api/v1/users/{user.id}"
    async with _client_with_db(db_session) as client:
        rotated = await client.post(f"{path}/regenerate-token")
        assert rotated.status_code == 200
        assert rotated.json()["data"]["auth_sync_result"] == "failed"
        assert rotated.json()["data"]["token"] != old_token
        assert user.auth_previous_token == old_token

        client_auth.fail_delete = False
        retried = await client.post(f"{path}/sync-auth")
        assert retried.status_code == 200
        assert retried.json()["data"]["auth_synced"] is True
        assert retried.json()["data"]["token"] == rotated.json()["data"]["token"]
    assert client_auth.deleted == [20]
    assert 10 in client_auth.tokens_by_id
    assert user.auth_previous_token is None


@pytest.mark.asyncio
async def test_delete_retains_account_and_attempts_both_revocations_on_failure(db_session, monkeypatch):
    class DeletionClient(FakeAuthClientContext):
        fail_current = True

        async def delete_token(self, token_id):
            if token_id == 10 and self.fail_current:
                raise AuthServiceError("Auth unavailable for current token")
            await super().delete_token(token_id)

    user = await UserService(db_session).create("A", "B", "1")
    user.auth_token_id = 10
    user.auth_previous_token = "previous"
    deletion_client = DeletionClient()
    deletion_client.tokens_by_id = {
        10: {"id": 10, "token": user.token, "user_id": str(user.id)},
        20: {"id": 20, "token": "previous", "user_id": str(user.id)},
    }
    await db_session.commit()
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: deletion_client)

    path = f"/api/v1/users/{user.id}"
    async with _client_with_db(db_session) as client:
        deletion = await client.delete(path)
        assert deletion.status_code == 502
        saved = await client.get(path)
        assert saved.status_code == 200
        assert saved.json()["data"]["auth_synced"] is False
        assert deletion_client.deleted == [20]
        assert user.auth_previous_token == "previous"

        deletion_client.fail_current = False
        assert (await client.delete(path)).status_code == 200
        assert (await client.get(path)).status_code == 404
    assert deletion_client.deleted == [20, 10]
