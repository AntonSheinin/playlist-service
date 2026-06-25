import pytest

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Channel, Group, StreamSource
from app.services.channel_service import ChannelService
from app.services.group_service import GroupService


@pytest.mark.asyncio
async def test_group_get_by_id_preserves_not_found_behavior(db_session):
    service = GroupService(db_session)

    with pytest.raises(NotFoundError) as exc_info:
        await service.get_by_id(999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "NOT_FOUND"
    assert exc_info.value.message == "Group not found"


@pytest.mark.asyncio
async def test_group_duplicate_check_excludes_current_row_on_update(db_session):
    service = GroupService(db_session)
    first = await service.create("News")
    second = await service.create("Movies")

    updated = await service.update(first.id, "News")
    assert updated.name == "News"

    with pytest.raises(DuplicateEntryError) as exc_info:
        await service.update(second.id, "News")

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == "Group 'News' already exists"


@pytest.mark.asyncio
async def test_group_reorder_ignores_missing_ids(db_session):
    service = GroupService(db_session)
    first = Group(name="First", sort_order=1)
    second = Group(name="Second", sort_order=2)
    db_session.add_all([first, second])
    await db_session.flush()

    await service.reorder(
        [
            {"id": first.id, "sort_order": 20},
            {"id": 999, "sort_order": 5},
        ]
    )

    assert (await service.get_by_id(first.id)).sort_order == 20
    assert (await service.get_by_id(second.id)).sort_order == 2


@pytest.mark.asyncio
async def test_channel_reorder_ignores_missing_ids(db_session):
    service = ChannelService(db_session)
    first = Channel(source=StreamSource.FLUSSONIC, stream_name="first", sort_order=1)
    second = Channel(source=StreamSource.NIMBLE, stream_name="second", sort_order=2)
    db_session.add_all([first, second])
    await db_session.flush()

    await service.reorder(
        [
            {"id": first.id, "sort_order": 20},
            {"id": 999, "sort_order": 5},
        ]
    )

    assert (await service.get_by_id(first.id)).sort_order == 20
    assert (await service.get_by_id(second.id)).sort_order == 2
