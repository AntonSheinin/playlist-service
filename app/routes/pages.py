from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.dependencies import DBSession
from app.exceptions import NotFoundError
from app.services.playlist_generator import PlaylistGenerator
from app.services.user_service import UserService

router = APIRouter()

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


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


@router.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str) -> HTMLResponse:
    """Serve React SPA for all non-API, non-static routes."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            content="<h1>Frontend not built</h1><p>Run <code>npm run build</code> in the frontend/ directory.</p>",
            status_code=503,
        )
    return HTMLResponse(content=index_path.read_text())
