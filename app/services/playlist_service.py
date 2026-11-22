from dataclasses import dataclass
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.exceptions import NotFoundError
from app.models import User
from app.services.playlist_generator import PlaylistGenerator
from app.services.user_service import UserService


@dataclass(frozen=True)
class GeneratedPlaylist:
    filename: str
    content: str
    channel_count: int

    @property
    def content_disposition(self) -> str:
        if self.filename.isascii():
            return f'attachment; filename="{self.filename}"'
        return f"attachment; filename*=UTF-8''{quote(self.filename, safe='')}"


class PlaylistService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(
        self, *, user_id: int | None = None, playlist_name: str | None = None
    ) -> GeneratedPlaylist:
        if (user_id is None) == (playlist_name is None):
            raise ValueError("Provide either user_id or playlist_name")
        condition = (
            User.id == user_id
            if user_id is not None
            else func.lower(User.playlist_name) == func.lower(playlist_name)
        )
        result = await self.db.execute(select(User).where(condition).options(raiseload("*")))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("Playlist not found" if playlist_name is not None else "User not found")
        channels = await UserService(self.db).resolve_channels(user.id)
        return GeneratedPlaylist(
            filename=f"{user.playlist_name}.m3u8",
            content=PlaylistGenerator().generate(user, channels),
            channel_count=len(channels),
        )
