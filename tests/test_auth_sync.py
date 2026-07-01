from datetime import datetime

import pytest

from app.clients.auth_service import AuthTokenCreate
from app.exceptions import AuthServiceError
from app.models import User, UserStatus
from app.services.auth_sync import AuthSyncService


class FakeAuthClient:
    def __init__(self, *, existing_token=None, fail_create=False):
        self.existing_token = existing_token
        self.fail_create = fail_create
        self.deleted: list[int] = []
        self.created: list[AuthTokenCreate] = []
        self.updated: list[tuple[int, object]] = []
        self.tokens_by_id: dict[int, dict] = {}

    async def create_token(self, data):
        if self.fail_create:
            raise AuthServiceError("create failed")
        self.created.append(data)
        return 123

    async def update_token(self, token_id, data):
        self.updated.append((token_id, data))

    async def get_token(self, token_id):
        return self.tokens_by_id[token_id]

    async def delete_token(self, token_id):
        self.deleted.append(token_id)

    async def find_token_by_value(self, token):
        return self.existing_token


class FakeAuthClientContext(FakeAuthClient):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.mark.asyncio
async def test_auth_sync_recreates_missing_auth_token_id(db_session):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="200",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=None,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClient()

    await AuthSyncService(db_session)._do_recreate(client, user)

    assert client.created
    assert client.created[0].user_id == str(user.id)
    assert client.created[0].meta is None
    assert user.auth_token_id == 123


@pytest.mark.asyncio
async def test_auth_sync_deletes_stale_token_by_value_before_recreate(db_session):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="201",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=10,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClient(existing_token={"id": 20, "token": "token"})

    await AuthSyncService(db_session)._do_recreate(client, user)

    assert client.deleted == [10, 20]
    assert client.created


@pytest.mark.asyncio
async def test_full_resync_recreates_wrong_auth_user_id(db_session, monkeypatch):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="204",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=10,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext()
    client.tokens_by_id[10] = {"id": 10, "token": "token", "user_id": "204"}
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    summary = await AuthSyncService(db_session).sync_all_users()

    assert summary["mismatched"] == 1
    assert client.deleted == [10]
    assert client.created[0].user_id == str(user.id)


@pytest.mark.asyncio
async def test_full_resync_recovers_wrong_token_value_then_deletes_unknown_pointed_token(
    db_session, monkeypatch
):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="205",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="correct-token",
        auth_token_id=10,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext(existing_token={"id": 20, "token": "correct-token"})
    client.tokens_by_id[10] = {"id": 10, "token": "other-token", "user_id": str(user.id)}
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    summary = await AuthSyncService(db_session).sync_all_users()

    assert summary["recovered"] == 1
    assert client.deleted == [20, 10]
    assert client.created[0].user_id == str(user.id)


@pytest.mark.asyncio
async def test_runtime_update_recovers_wrong_token_value_without_deleting_pointed_token(
    db_session, monkeypatch
):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="206",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="correct-token",
        auth_token_id=10,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext(existing_token={"id": 20, "token": "correct-token"})
    client.tokens_by_id[10] = {"id": 10, "token": "other-token", "user_id": str(user.id)}
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    await AuthSyncService(db_session).sync_user_update(user)

    assert client.deleted == [20]
    assert client.created[0].user_id == str(user.id)


@pytest.mark.asyncio
async def test_sync_users_by_ids_verifies_auth_user_id_before_patch(db_session, monkeypatch):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="207",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=10,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext()
    client.tokens_by_id[10] = {"id": 10, "token": "token", "user_id": "207"}
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    await AuthSyncService(db_session).sync_users_by_ids([user.id])

    assert client.updated == []
    assert client.deleted == [10]
    assert client.created[0].user_id == str(user.id)


@pytest.mark.asyncio
async def test_full_resync_recreates_to_clear_auth_valid_until(db_session, monkeypatch):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="208",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=10,
        valid_until=None,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext()
    client.tokens_by_id[10] = {
        "id": 10,
        "token": "token",
        "user_id": str(user.id),
        "valid_until": datetime(2026, 1, 1).isoformat(),
    }
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    summary = await AuthSyncService(db_session).sync_all_users()

    assert summary["recreated"] == 1
    assert client.updated == []
    assert client.deleted == [10]
    assert client.created[0].valid_until is None


@pytest.mark.asyncio
async def test_full_resync_recreates_when_explicit_valid_from_differs(db_session, monkeypatch):
    valid_from = datetime(2026, 1, 2)
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="209",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=10,
        valid_from=valid_from,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext()
    client.tokens_by_id[10] = {
        "id": 10,
        "token": "token",
        "user_id": str(user.id),
        "valid_from": datetime(2026, 1, 1).isoformat(),
        "valid_until": None,
    }
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    summary = await AuthSyncService(db_session).sync_all_users()

    assert summary["recreated"] == 1
    assert client.updated == []
    assert client.deleted == [10]
    assert client.created[0].valid_from == valid_from


@pytest.mark.asyncio
async def test_auth_sync_recreate_failure_propagates_for_explicit_recreate(db_session):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="202",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
    )
    db_session.add(user)
    await db_session.flush()

    with pytest.raises(AuthServiceError):
        await AuthSyncService(db_session)._do_recreate(FakeAuthClient(fail_create=True), user)


@pytest.mark.asyncio
async def test_auth_sync_update_swallows_recreate_failure(monkeypatch, db_session):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="203",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        auth_token_id=10,
    )
    db_session.add(user)
    await db_session.flush()
    client = FakeAuthClientContext(fail_create=True)
    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", lambda: client)

    await AuthSyncService(db_session).sync_user_update(user, recreate_token=True)

    assert client.deleted == [10]
