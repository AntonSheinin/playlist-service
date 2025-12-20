from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Base

T = TypeVar("T", bound=Base)


class BaseService(Generic[T]):
    """Base service with common CRUD operations."""

    model_class: type[T]
    not_found_message: str = "Item not found"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, item_id: int) -> T:
        """Get item by ID."""
        stmt = select(self.model_class).where(self.model_class.id == item_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()

        if item is None:
            raise NotFoundError(self.not_found_message)

        return item

    async def check_unique(
        self,
        field: str,
        value: Any,
        exclude_id: int | None = None,
        message: str | None = None,
    ) -> None:
        """Check that a field value is unique."""
        column = getattr(self.model_class, field)
        stmt = select(self.model_class).where(column == value)

        if exclude_id is not None:
            stmt = stmt.where(self.model_class.id != exclude_id)

        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(message or f"{field} '{value}' already exists")

    async def reorder(self, order: list[dict[str, int]]) -> None:
        """Reorder items by updating sort_order. Expects list of {id, sort_order}."""
        for item in order:
            stmt = select(self.model_class).where(self.model_class.id == item["id"])
            result = await self.db.execute(stmt)
            obj = result.scalar_one_or_none()
            if obj:
                obj.sort_order = item["sort_order"]
        await self.db.flush()
