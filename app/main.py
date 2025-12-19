import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings, setup_logging
from app.exceptions import (
    AuthServiceError,
    ChannelNotOrphanedError,
    DuplicateEntryError,
    FlussonicError,
    InvalidCredentialsError,
    NotFoundError,
    PlaylistServiceError,
    UnauthorizedError,
    ValidationError,
)
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

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(api_router)
app.include_router(pages_router)


# Exception handlers
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(DuplicateEntryError)
async def duplicate_entry_handler(request: Request, exc: DuplicateEntryError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(
    request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(ChannelNotOrphanedError)
async def channel_not_orphaned_handler(
    request: Request, exc: ChannelNotOrphanedError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(FlussonicError)
async def flussonic_error_handler(request: Request, exc: FlussonicError) -> JSONResponse:
    logger.error("Flussonic error: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(AuthServiceError)
async def auth_service_error_handler(request: Request, exc: AuthServiceError) -> JSONResponse:
    logger.error("Auth service error: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(PlaylistServiceError)
async def playlist_service_error_handler(
    request: Request, exc: PlaylistServiceError
) -> JSONResponse:
    logger.error("Internal error: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
