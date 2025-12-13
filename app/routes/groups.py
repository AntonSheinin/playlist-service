from fastapi import APIRouter

from app.dependencies import CurrentAdminId, DBSession
from app.schemas.common import MessageResponse, SuccessResponse
from app.schemas.group import (
    GroupCreate,
    GroupReorderRequest,
    GroupResponse,
    GroupUpdate,
    GroupWithCount,
)
from app.services.group_service import GroupService

router = APIRouter()


@router.get("", response_model=SuccessResponse[list[GroupWithCount]])
async def list_groups(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[GroupWithCount]]:
    """List all groups with channel counts."""
    service = GroupService(db)
    groups = await service.get_all()

    result = []
    for group in groups:
        count = await service.get_channel_count(group.id)
        group_data = GroupWithCount(
            id=group.id,
            name=group.name,
            sort_order=group.sort_order,
            created_at=group.created_at,
            updated_at=group.updated_at,
            channel_count=count,
        )
        result.append(group_data)

    return SuccessResponse(data=result)


@router.post("", response_model=SuccessResponse[GroupResponse])
async def create_group(
    data: GroupCreate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[GroupResponse]:
    """Create a new group."""
    service = GroupService(db)
    group = await service.create(data.name)
    return SuccessResponse(data=GroupResponse.model_validate(group))


@router.patch("/{group_id}", response_model=SuccessResponse[GroupResponse])
async def update_group(
    group_id: int,
    data: GroupUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[GroupResponse]:
    """Update a group."""
    service = GroupService(db)
    group = await service.update(group_id, data.name)
    return SuccessResponse(data=GroupResponse.model_validate(group))


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Delete a group."""
    service = GroupService(db)
    affected = await service.delete(group_id)
    return MessageResponse(message=f"Group deleted. {affected} channels unassigned.")


@router.post("/reorder", response_model=MessageResponse)
async def reorder_groups(
    data: GroupReorderRequest,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Reorder groups."""
    service = GroupService(db)
    await service.reorder([{"id": item.id, "sort_order": item.sort_order} for item in data.order])
    return MessageResponse(message="Groups reordered successfully")
