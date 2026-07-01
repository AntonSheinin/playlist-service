"""Normalize Auth Backend user_id values and run full Auth resync.

Run from the Playlist Service environment. For normalization modes, provide
AUTH_DATABASE_URL for direct access to the Auth Backend database.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.services.auth_sync import AuthSyncService
from app.services.database import async_session_factory


@dataclass(frozen=True)
class PlaylistUser:
    id: int
    agreement_number: str
    token: str
    auth_token_id: int | None

    @property
    def auth_user_id(self) -> str:
        return str(self.id)


@dataclass
class AuthState:
    tokens: list[dict[str, Any]]
    sessions: list[dict[str, Any]]
    logs: list[dict[str, Any]]


def to_async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


async def load_playlist_users() -> list[PlaylistUser]:
    async with async_session_factory() as session:
        result = await session.execute(text(
            "SELECT id, agreement_number, token, auth_token_id FROM users ORDER BY id"
        ))
        return [
            PlaylistUser(
                id=row.id,
                agreement_number=row.agreement_number,
                token=row.token,
                auth_token_id=row.auth_token_id,
            )
            for row in result
        ]


async def load_auth_state(engine: AsyncEngine) -> AuthState:
    async with engine.connect() as conn:
        tokens = [
            dict(row._mapping)
            for row in (await conn.execute(text("SELECT id, token, user_id, meta FROM tokens ORDER BY id")))
        ]
        sessions = [
            dict(row._mapping)
            for row in (await conn.execute(text("SELECT id, token_id, user_id FROM active_sessions ORDER BY id")))
        ]
        logs = [
            dict(row._mapping)
            for row in (await conn.execute(text("SELECT id, user_id FROM access_logs ORDER BY id")))
        ]
    return AuthState(tokens=tokens, sessions=sessions, logs=logs)


def describe_state(users: list[PlaylistUser], state: AuthState) -> dict[str, int]:
    token_to_user = {user.token: user for user in users}
    agreement_to_user_id = {user.agreement_number: user.auth_user_id for user in users}
    known_user_ids = {user.auth_user_id for user in users}
    referenced_token_ids = {
        user.auth_token_id for user in users if user.auth_token_id is not None
    }

    counts = {
        "playlist_users": len(users),
        "tokens_normalized": 0,
        "tokens_rewrite": 0,
        "tokens_clear_meta": 0,
        "tokens_unknown_delete": 0,
        "tokens_mismatched_referenced": 0,
        "sessions_normalized": 0,
        "sessions_rewrite": 0,
        "sessions_delete": 0,
        "logs_normalized": 0,
        "logs_rewrite": 0,
        "logs_null": 0,
    }

    for token in state.tokens:
        playlist_user = token_to_user.get(str(token["token"]))
        if playlist_user is None:
            if token["id"] in referenced_token_ids:
                counts["tokens_mismatched_referenced"] += 1
            else:
                counts["tokens_unknown_delete"] += 1
            continue

        expected_user_id = playlist_user.auth_user_id
        if str(token["user_id"]) == expected_user_id:
            counts["tokens_normalized"] += 1
        else:
            counts["tokens_rewrite"] += 1
        if token.get("meta"):
            counts["tokens_clear_meta"] += 1

    for session in state.sessions:
        user_id = str(session["user_id"])
        if user_id in known_user_ids:
            counts["sessions_normalized"] += 1
        elif user_id in agreement_to_user_id:
            counts["sessions_rewrite"] += 1
        else:
            counts["sessions_delete"] += 1

    for log in state.logs:
        if log["user_id"] is None:
            counts["logs_null"] += 1
            continue
        user_id = str(log["user_id"])
        if user_id in known_user_ids:
            counts["logs_normalized"] += 1
        elif user_id in agreement_to_user_id:
            counts["logs_rewrite"] += 1
        else:
            counts["logs_null"] += 1

    return counts


async def apply_normalization(engine: AsyncEngine, users: list[PlaylistUser], state: AuthState) -> None:
    token_to_user = {user.token: user for user in users}
    agreement_to_user_id = {user.agreement_number: user.auth_user_id for user in users}
    known_user_ids = {user.auth_user_id for user in users}
    referenced_token_ids = {
        user.auth_token_id for user in users if user.auth_token_id is not None
    }

    async with engine.begin() as conn:
        for token in state.tokens:
            token_id = token["id"]
            playlist_user = token_to_user.get(str(token["token"]))
            if playlist_user is None:
                if token_id in referenced_token_ids:
                    print(
                        f"mismatch: auth token {token_id} is referenced by Playlist but has unknown token value; keeping for resync"
                    )
                    continue
                await conn.execute(
                    text("DELETE FROM active_sessions WHERE token_id = :token_id"),
                    {"token_id": token_id},
                )
                await conn.execute(text("DELETE FROM tokens WHERE id = :id"), {"id": token_id})
                continue

            await conn.execute(
                text("UPDATE tokens SET user_id = :user_id, meta = NULL WHERE id = :id"),
                {"id": token_id, "user_id": playlist_user.auth_user_id},
            )

        for session in state.sessions:
            row_id = session["id"]
            user_id = str(session["user_id"])
            if user_id in known_user_ids:
                continue
            if user_id in agreement_to_user_id:
                await conn.execute(
                    text("UPDATE active_sessions SET user_id = :user_id WHERE id = :id"),
                    {"id": row_id, "user_id": agreement_to_user_id[user_id]},
                )
            else:
                await conn.execute(text("DELETE FROM active_sessions WHERE id = :id"), {"id": row_id})

        for log in state.logs:
            row_id = log["id"]
            if log["user_id"] is None:
                continue
            user_id = str(log["user_id"])
            if user_id in known_user_ids:
                continue
            if user_id in agreement_to_user_id:
                await conn.execute(
                    text("UPDATE access_logs SET user_id = :user_id WHERE id = :id"),
                    {"id": row_id, "user_id": agreement_to_user_id[user_id]},
                )
            else:
                await conn.execute(text("UPDATE access_logs SET user_id = NULL WHERE id = :id"), {"id": row_id})


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(title)
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")


async def normalize_auth_db(*, apply: bool) -> None:
    auth_database_url = os.environ.get("AUTH_DATABASE_URL")
    if not auth_database_url:
        raise RuntimeError("AUTH_DATABASE_URL is required for dry-run/apply normalization")

    engine = create_async_engine(to_async_database_url(auth_database_url))
    try:
        users = await load_playlist_users()
        state = await load_auth_state(engine)
        counts = describe_state(users, state)
        print_counts("Auth identity normalization dry-run" if not apply else "Auth identity normalization plan", counts)
        if apply:
            await apply_normalization(engine, users, state)
            updated_state = await load_auth_state(engine)
            print_counts("Auth identity normalization result", describe_state(users, updated_state))
    finally:
        await engine.dispose()


async def full_resync() -> None:
    async with async_session_factory() as session:
        summary = await AuthSyncService(session).sync_all_users()
        await session.commit()
    print_counts("Full Auth resync result", summary)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Maintain Auth Backend Playlist user identity")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report Auth DB normalization actions")
    mode.add_argument("--apply", action="store_true", help="Apply Auth DB normalization actions")
    mode.add_argument("--full-resync", action="store_true", help="Resync all users through Auth API")
    args = parser.parse_args()

    if args.full_resync:
        await full_resync()
    else:
        await normalize_auth_db(apply=args.apply)


if __name__ == "__main__":
    asyncio.run(main())
