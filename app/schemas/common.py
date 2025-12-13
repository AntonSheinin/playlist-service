from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    success: bool = False
    error: ErrorDetail


class PaginatedData(BaseModel, Generic[T]):
    """Paginated data structure."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    success: bool = True
    data: PaginatedData[T]


class MessageResponse(BaseModel):
    """Simple message response."""

    success: bool = True
    message: str
