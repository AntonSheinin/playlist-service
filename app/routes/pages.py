from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.dependencies import DBSession
from app.services.playlist_service import PlaylistService

router = APIRouter()

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
SPA_HTML_HEADERS = {"Cache-Control": "no-store"}


@router.get("/{playlist_name}.m3u8", response_class=PlainTextResponse)
async def public_playlist(playlist_name: str, db: DBSession) -> PlainTextResponse:
    """Serve a public playlist by filename."""
    playlist = await PlaylistService(db).generate(playlist_name=playlist_name)
    return PlainTextResponse(
        content=playlist.content,
        media_type="audio/x-mpegurl",
        headers={"Content-Disposition": playlist.content_disposition},
    )


@router.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str) -> HTMLResponse:
    """Serve React SPA for all non-API, non-static routes."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse(
            content="<h1>Frontend not built</h1><p>Run <code>npm run build</code> in the frontend/ directory.</p>",
            status_code=503,
            headers=SPA_HTML_HEADERS,
        )
    return HTMLResponse(content=index_path.read_text(), headers=SPA_HTML_HEADERS)
