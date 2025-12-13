#!/usr/bin/env python3
"""Script to create an admin user for the Playlist Service."""

import asyncio
import getpass
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Admin
from app.services.database import async_session_factory
from app.utils.password import hash_password


async def create_admin(username: str, password: str) -> None:
    """Create an admin user."""
    async with async_session_factory() as session:
        # Check if username already exists
        stmt = select(Admin).where(Admin.username == username)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Error: Admin '{username}' already exists.")
            sys.exit(1)

        # Create admin
        admin = Admin(
            username=username,
            password_hash=hash_password(password),
        )
        session.add(admin)
        await session.commit()

        print(f"Admin '{username}' created successfully.")


def main() -> None:
    """Main entry point."""
    print("=" * 50)
    print("Playlist Service - Create Admin User")
    print("=" * 50)
    print()

    # Get username
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Username: ").strip()

    if not username:
        print("Error: Username cannot be empty.")
        sys.exit(1)

    # Get password
    password = getpass.getpass("Password: ")
    if not password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("Error: Passwords do not match.")
        sys.exit(1)

    if len(password) < 6:
        print("Error: Password must be at least 6 characters.")
        sys.exit(1)

    # Create admin
    asyncio.run(create_admin(username, password))


if __name__ == "__main__":
    main()
