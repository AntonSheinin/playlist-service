from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from scripts.auth_identity_maintenance import (
    AuthState,
    PlaylistUser,
    apply_normalization,
    describe_state,
    load_auth_state,
)


async def create_auth_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE tokens (id INTEGER PRIMARY KEY, token TEXT, user_id TEXT, meta TEXT)"))
        await conn.execute(text("CREATE TABLE active_sessions (id INTEGER PRIMARY KEY, token_id INTEGER, user_id TEXT)"))
        await conn.execute(text("CREATE TABLE access_logs (id INTEGER PRIMARY KEY, user_id TEXT NULL)"))
    return engine


async def test_auth_identity_normalization_reports_expected_actions():
    users = [
        PlaylistUser(id=10, agreement_number="A-10", token="managed-old", auth_token_id=1),
        PlaylistUser(id=11, agreement_number="A-11", token="managed-new", auth_token_id=2),
    ]
    state = AuthState(
        tokens=[
            {"id": 1, "token": "managed-old", "user_id": "A-10", "meta": '{"name":"old"}'},
            {"id": 2, "token": "managed-new", "user_id": "11", "meta": None},
            {"id": 3, "token": "unknown", "user_id": "external", "meta": None},
        ],
        sessions=[
            {"id": 1, "token_id": 1, "user_id": "A-10"},
            {"id": 2, "token_id": 2, "user_id": "11"},
            {"id": 3, "token_id": 3, "user_id": "external"},
        ],
        logs=[
            {"id": 1, "user_id": "A-10"},
            {"id": 2, "user_id": "11"},
            {"id": 3, "user_id": "external"},
        ],
    )

    counts = describe_state(users, state)

    assert counts["tokens_rewrite"] == 1
    assert counts["tokens_normalized"] == 1
    assert counts["tokens_clear_meta"] == 1
    assert counts["tokens_unknown_delete"] == 1
    assert counts["sessions_rewrite"] == 1
    assert counts["sessions_delete"] == 1
    assert counts["logs_rewrite"] == 1
    assert counts["logs_null"] == 1


async def test_auth_identity_normalization_apply_updates_and_deletes_rows():
    engine = await create_auth_engine()
    users = [PlaylistUser(id=10, agreement_number="A-10", token="managed", auth_token_id=1)]
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO tokens (id, token, user_id, meta) VALUES (1, 'managed', 'A-10', '{\"n\":\"A\"}')")
            )
            await conn.execute(
                text("INSERT INTO tokens (id, token, user_id, meta) VALUES (2, 'unknown', 'external', NULL)")
            )
            await conn.execute(text("INSERT INTO active_sessions (id, token_id, user_id) VALUES (1, 1, 'A-10')"))
            await conn.execute(text("INSERT INTO active_sessions (id, token_id, user_id) VALUES (2, 2, 'external')"))
            await conn.execute(text("INSERT INTO access_logs (id, user_id) VALUES (1, 'A-10')"))
            await conn.execute(text("INSERT INTO access_logs (id, user_id) VALUES (2, 'external')"))

        state = await load_auth_state(engine)
        await apply_normalization(engine, users, state)

        async with engine.connect() as conn:
            tokens = [
                dict(row._mapping)
                for row in (await conn.execute(text("SELECT id, user_id, meta FROM tokens ORDER BY id")))
            ]
            sessions = [
                dict(row._mapping)
                for row in (await conn.execute(text("SELECT id, user_id FROM active_sessions ORDER BY id")))
            ]
            logs = [
                dict(row._mapping)
                for row in (await conn.execute(text("SELECT id, user_id FROM access_logs ORDER BY id")))
            ]

        assert tokens == [{"id": 1, "user_id": "10", "meta": None}]
        assert sessions == [{"id": 1, "user_id": "10"}]
        assert logs == [{"id": 1, "user_id": "10"}, {"id": 2, "user_id": None}]
    finally:
        await engine.dispose()
