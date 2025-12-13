from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.services.database import get_db

# Type aliases for dependency injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_serializer(settings: AppSettings) -> URLSafeTimedSerializer:
    """Get URL-safe timed serializer for session tokens."""
    return URLSafeTimedSerializer(settings.secret_key)


async def get_current_admin_id(
    settings: AppSettings,
    session_id: str | None = Cookie(default=None),
) -> int:
    """
    Get current authenticated admin ID from session cookie.
    Raises 401 if not authenticated.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Not authenticated"},
        )

    serializer = get_serializer(settings)

    try:
        admin_id = serializer.loads(session_id, max_age=settings.session_timeout)
        return admin_id
    except SignatureExpired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Session expired"},
        )
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid session"},
        )


CurrentAdminId = Annotated[int, Depends(get_current_admin_id)]


def create_session_token(admin_id: int, settings: Settings) -> str:
    """Create a signed session token for an admin."""
    serializer = URLSafeTimedSerializer(settings.secret_key)
    return serializer.dumps(admin_id)
