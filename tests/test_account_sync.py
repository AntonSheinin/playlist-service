import pytest

from app.exceptions import AuthServiceError
from app.models import Channel, Package, StreamSource
from app.services.user_service import UserService
from test_api_contract import _client_with_db
from test_auth_sync import FakeAuthClientContext


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
