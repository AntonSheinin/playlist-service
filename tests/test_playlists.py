from datetime import datetime
from unittest.mock import AsyncMock
from urllib.parse import quote

import pytest
from sqlalchemy import select

from app.dependencies import get_current_admin_id
from app.exceptions import DuplicateEntryError
from app.main import app
from app.models import Channel, StreamSource, User
from app.services.playlist_service import PlaylistService
from app.services.user_service import UserService
from app.utils.playlist_name import generate_playlist_name, validate_playlist_name
from test_integrations_api import _client_with_db, _headers


def test_default_name_preserves_existing_sanitization_and_length():
    assert generate_playlist_name("Al ice!", "Иванов", "A/123") == "Иванов_Al_ice_A123"
    assert len(generate_playlist_name("A" * 100, "B" * 100, "C" * 100)) == 302
    assert validate_playlist_name("Émission_¹_123") == "Émission_¹_123"


@pytest.mark.asyncio
async def test_admin_creation_initializes_name_and_keeps_integration_contract(db_session, monkeypatch):
    sync = AsyncMock()
    monkeypatch.setattr("app.services.auth_sync.AuthSyncService.sync_user_create", sync)
    app.dependency_overrides[get_current_admin_id] = lambda: 1
    try:
        async with _client_with_db(db_session) as client:
            response = await client.post("/api/v1/users", json={
                "first_name": "Alice", "last_name": "Smith", "agreement_number": "AG/12"
            })
            assert response.status_code == 200
            user = response.json()["data"]
            assert user["playlist_name"] == "Smith_Alice_AG12"
            integration = await client.get(
                f"/api/v1/integrations/users/{user['id']}", headers=_headers()
            )
            assert integration.status_code == 200
            assert set(integration.json()["data"]) == {
                "user_id", "first_name", "last_name", "agreement_number", "status",
                "portal_allowed", "max_sessions", "valid_until",
            }
    finally:
        app.dependency_overrides.pop(get_current_admin_id, None)
    sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_rename_updates_all_playlist_outputs_without_auth_sync(db_session, monkeypatch):
    valid_from = datetime(2026, 1, 1, 9, 15, 30, 123456)
    valid_until = datetime(2026, 12, 31, 12, 30, 45, 654321)
    user = await UserService(db_session).create(
        "Alice", "Smith", "12", valid_from=valid_from, valid_until=valid_until
    )
    user.channels = [Channel(source=StreamSource.FLUSSONIC, stream_name="news")]
    await db_session.commit()
    user_id, token = user.id, user.token
    sync = AsyncMock()
    monkeypatch.setattr("app.services.auth_sync.AuthSyncService.sync_user_update", sync)
    app.dependency_overrides[get_current_admin_id] = lambda: 1
    try:
        async with _client_with_db(db_session) as client:
            original = await client.get("/Smith_Alice_12.m3u8")
            renamed = await client.patch(
                f"/api/v1/users/{user_id}", json={"playlist_name": "Новости_12"}
            )
            assert renamed.status_code == 200
            assert renamed.json()["data"]["token"] == token
            assert renamed.json()["data"]["valid_from"] == valid_from.isoformat()
            assert renamed.json()["data"]["valid_until"] == valid_until.isoformat()
            public = await client.get(f"/{quote('Новости_12')}.m3u8")
            download = await client.get(f"/api/v1/users/{user_id}/playlist")
            preview = await client.get(f"/api/v1/users/{user_id}/playlist/preview")
            old = await client.get("/Smith_Alice_12.m3u8")
            personal = await client.patch(
                f"/api/v1/users/{user_id}", json={"first_name": "Updated"}
            )
    finally:
        app.dependency_overrides.pop(get_current_admin_id, None)
    sync.assert_not_awaited()
    assert old.status_code == 404
    assert original.status_code == public.status_code == download.status_code == 200
    assert public.text == download.text == original.text == preview.json()["data"]["content"]
    assert preview.json()["data"]["filename"] == "Новости_12.m3u8"
    assert preview.json()["data"]["channel_count"] == 1
    assert public.headers["content-disposition"] == download.headers["content-disposition"]
    assert "filename*=UTF-8''" + quote("Новости_12.m3u8") in public.headers["content-disposition"]
    assert personal.json()["data"]["playlist_name"] == "Новости_12"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [None, "", " ", "bad/name", "name.m3u8", "a" * 303])
async def test_invalid_rename_preserves_saved_name(db_session, name):
    user = await UserService(db_session).create("A", "B", "1")
    await db_session.commit()
    user_id = user.id
    app.dependency_overrides[get_current_admin_id] = lambda: 1
    try:
        async with _client_with_db(db_session) as client:
            response = await client.patch(
                f"/api/v1/users/{user_id}", json={"playlist_name": name}
            )
            assert response.status_code == 422
            original = await client.get("/B_A_1.m3u8")
            assert original.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_admin_id, None)


@pytest.mark.asyncio
async def test_duplicate_default_and_rename_return_conflict(db_session):
    first = await UserService(db_session).create("A", "B", "1/2")
    second = await UserService(db_session).create("C", "D", "3")
    await db_session.commit()
    first_id, second_id = first.id, second.id
    app.dependency_overrides[get_current_admin_id] = lambda: 1
    try:
        async with _client_with_db(db_session) as client:
            duplicate = await client.post("/api/v1/users", json={
                "first_name": "A", "last_name": "B", "agreement_number": "12"
            })
            assert duplicate.status_code == 409
            rename = await client.patch(
                f"/api/v1/users/{second_id}", json={"playlist_name": "b_a_12", "first_name": "Changed"}
            )
            assert rename.status_code == 409
            assert rename.json()["error"]["code"] == "DUPLICATE_ENTRY"
            saved = await client.get(f"/api/v1/users/{second_id}")
            assert saved.json()["data"]["playlist_name"] == "D_C_3"
            assert saved.json()["data"]["first_name"] == "C"
            assert (await client.get("/D_C_3.m3u8")).status_code == 200
            same = await client.patch(
                f"/api/v1/users/{first_id}", json={"playlist_name": "b_a_12"}
            )
            assert same.status_code == 200
            # A later failure in the same update must also undo the flushed rename.
            failed = await client.patch(
                f"/api/v1/users/{second_id}",
                json={"playlist_name": "Replacement", "agreement_number": "1/2"},
            )
            assert failed.status_code == 409
            assert (await client.get("/D_C_3.m3u8")).status_code == 200
            assert (await client.get("/Replacement.m3u8")).status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_admin_id, None)


@pytest.mark.asyncio
async def test_database_conflict_is_translated_and_rolls_back(db_session, monkeypatch):
    first = await UserService(db_session).create("A", "B", "1")
    second = await UserService(db_session).create("C", "D", "2")
    await db_session.commit()
    first_name, second_id = first.playlist_name, second.id
    monkeypatch.setattr(UserService, "_ensure_playlist_name_available", AsyncMock())
    with pytest.raises(DuplicateEntryError):
        await UserService(db_session).update(second_id, playlist_name=first_name)
    await db_session.rollback()
    saved = await db_session.scalar(select(User).where(User.id == second_id))
    assert saved.playlist_name == "D_C_2"
    assert (await PlaylistService(db_session).generate(playlist_name="d_c_2")).filename == "D_C_2.m3u8"
