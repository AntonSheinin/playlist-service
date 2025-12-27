from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import DBSession
from app.exceptions import NotFoundError
from app.services.playlist_generator import PlaylistGenerator
from app.services.user_service import UserService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Render login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    """Render dashboard page."""
    return templates.TemplateResponse("dashboard/index.html", {"request": request})


@router.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request) -> HTMLResponse:
    """Render channels page."""
    return templates.TemplateResponse("channels/list.html", {"request": request})


@router.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request) -> HTMLResponse:
    """Render groups page."""
    return templates.TemplateResponse("groups/list.html", {"request": request})


@router.get("/packages", response_class=HTMLResponse)
async def packages_page(request: Request) -> HTMLResponse:
    """Render packages and tariffs page."""
    return templates.TemplateResponse("packages/list.html", {"request": request})


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request) -> HTMLResponse:
    """Render users list page."""
    return templates.TemplateResponse("users/list.html", {"request": request})


@router.get("/users/new", response_class=HTMLResponse)
async def user_new_page(request: Request) -> HTMLResponse:
    """Render new user page."""
    return templates.TemplateResponse("users/detail.html", {"request": request, "user_id": None})


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail_page(request: Request, user_id: int) -> HTMLResponse:
    """Render user detail page."""
    return templates.TemplateResponse("users/detail.html", {"request": request, "user_id": user_id})


@router.get("/{playlist_name}.m3u8", response_class=PlainTextResponse)
async def public_playlist(playlist_name: str, db: DBSession) -> PlainTextResponse:
    """Serve a public playlist by filename."""
    generator = PlaylistGenerator()
    user_service = UserService(db)

    user = await user_service.get_by_playlist_name(playlist_name)
    if user is None:
        raise NotFoundError("Playlist not found")

    channels = await user_service.resolve_channels(user.id)
    content = generator.generate(user, channels)
    filename = generator.get_filename(user)

    return PlainTextResponse(
        content=content,
        media_type="audio/x-mpegurl",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
