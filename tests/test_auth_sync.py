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

    async def create_token(self, data):
        if self.fail_create:
            raise AuthServiceError("create failed")
        self.created.append(data)
        return 123

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
