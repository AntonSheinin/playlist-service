import asyncio
import logging

import pytest
from fastapi import HTTPException

from app.exceptions import NotFoundError, PlaylistServiceError
from app.services import database as database_service


class RecordingDatabaseSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_level"),
    [
        (NotFoundError("User not found"), logging.DEBUG),
        (PlaylistServiceError("Server failure"), logging.ERROR),
        (HTTPException(status_code=503, detail="Dependency failure"), logging.ERROR),
        (RuntimeError("Unexpected failure"), logging.ERROR),
    ],
)
async def test_database_boundary_rolls_back_and_logs_at_expected_level(
    monkeypatch,
    caplog,
    error,
    expected_level,
):
    session = RecordingDatabaseSession()
    monkeypatch.setattr(database_service, "async_session_factory", lambda: session)
    caplog.set_level(logging.DEBUG, logger="app.services.database")
    dependency = database_service.get_db()

    assert await anext(dependency) is session
    with pytest.raises(type(error)):
        await dependency.athrow(error)

    assert session.rollbacks == 1
    assert session.commits == 0
    records = [record for record in caplog.records if "rolling back transaction" in record.message]
    assert len(records) == 1
    assert records[0].levelno == expected_level


@pytest.mark.asyncio
async def test_database_boundary_rolls_back_cancellation_without_error_log(monkeypatch, caplog):
    session = RecordingDatabaseSession()
    monkeypatch.setattr(database_service, "async_session_factory", lambda: session)
    caplog.set_level(logging.DEBUG, logger="app.services.database")
    dependency = database_service.get_db()

    assert await anext(dependency) is session
    with pytest.raises(asyncio.CancelledError):
        await dependency.athrow(asyncio.CancelledError())

    assert session.rollbacks == 1
    assert session.commits == 0
    assert not any("rolling back transaction" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_database_boundary_commits_successful_request(monkeypatch):
    session = RecordingDatabaseSession()
    monkeypatch.setattr(database_service, "async_session_factory", lambda: session)
    dependency = database_service.get_db()

    assert await anext(dependency) is session
    with pytest.raises(StopAsyncIteration):
        await anext(dependency)

    assert session.commits == 1
    assert session.rollbacks == 0
