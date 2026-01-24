from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, UnauthorizedError
from app.models import Admin
from app.utils.password import hash_password, verify_password


class AdminAuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def authenticate(self, username: str, password: str) -> Admin:
        """Authenticate admin user."""
        stmt = select(Admin).where(Admin.username == username)
        result = await self.db.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None or not verify_password(password, admin.password_hash):
            raise UnauthorizedError("Invalid credentials")

        return admin

    async def get_by_id(self, admin_id: int) -> Admin:
        """Get admin by ID."""
        stmt = select(Admin).where(Admin.id == admin_id)
        result = await self.db.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            raise NotFoundError("Admin not found")

        return admin

    async def create_admin(self, username: str, password: str) -> Admin:
        """Create a new admin user."""
        admin = Admin(
            username=username,
            password_hash=hash_password(password),
        )
        self.db.add(admin)
        await self.db.flush()
        return await self.get_by_id(admin.id)
