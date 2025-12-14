from fastapi import APIRouter, Response

from app.dependencies import AppSettings, CurrentAdminId, DBSession, create_session_token
from app.schemas import AdminResponse, ErrorResponse, LoginRequest, MessageResponse, SuccessResponse
from app.services.admin_auth import AdminAuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=SuccessResponse[AdminResponse],
    responses={401: {"model": ErrorResponse}},
)
async def login(
    data: LoginRequest,
    response: Response,
    db: DBSession,
    settings: AppSettings,
) -> SuccessResponse[AdminResponse]:
    """Authenticate admin and set session cookie."""
    service = AdminAuthService(db)
    admin = await service.authenticate(data.username, data.password)

    # Create session token and set cookie
    token = create_session_token(admin.id, settings)
    response.set_cookie(
        key="session_id",
        value=token,
        max_age=settings.session_timeout,
        httponly=True,
        samesite="lax",
    )

    return SuccessResponse(data=AdminResponse.model_validate(admin))


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """Logout and clear session cookie."""
    response.delete_cookie(key="session_id")
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=SuccessResponse[AdminResponse],
    responses={401: {"model": ErrorResponse}},
)
async def get_current_admin(
    admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[AdminResponse]:
    """Get current authenticated admin info."""
    service = AdminAuthService(db)
    admin = await service.get_by_id(admin_id)
    return SuccessResponse(data=AdminResponse.model_validate(admin))
