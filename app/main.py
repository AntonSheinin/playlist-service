import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings, setup_logging
from app.exceptions import PlaylistServiceError
from app.routes import api_router, pages_router
from app.services.database import engine

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    logger.info("Playlist Service starting up")
    yield
    logger.info("Playlist Service shutting down")
    await engine.dispose()


app = FastAPI(
    title="Playlist Service",
    description="IPTV Playlist Service for Flussonic Media Server",
    version="1.0.0",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
(MEDIA_ROOT / "logos").mkdir(parents=True, exist_ok=True)

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

# Mount static files
app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")
if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS)), name="assets")

# Include routers (API first, then pages with SPA catch-all last)
app.include_router(api_router)
app.include_router(pages_router)


@app.exception_handler(PlaylistServiceError)
async def playlist_service_error_handler(
    request: Request, exc: PlaylistServiceError
) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("%s: %s", exc.__class__.__name__, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
