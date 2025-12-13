from fastapi import APIRouter

from app.routes import auth, channels, dashboard, groups, lookup, packages, pages, tariffs, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(packages.router, prefix="/packages", tags=["packages"])
api_router.include_router(tariffs.router, prefix="/tariffs", tags=["tariffs"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(lookup.router, prefix="/lookup", tags=["lookup"])

pages_router = pages.router
