from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str
    password: str


class AdminResponse(BaseModel):
    """Admin user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
