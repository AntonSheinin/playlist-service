"""Backfill Portal accounts or verify the generated request sizes before rollout."""

import argparse
import asyncio

from sqlalchemy import select

from app.clients.portal import PortalClient, encode_snapshot
from app.config import get_settings
from app.exceptions import NotFoundError, PortalSyncError, PortalUnavailableError
from app.models import User
from app.services.database import async_session_factory
from app.services.portal_sync import PortalSyncService
from app.services.user_service import UserService


async def backfill(*, check_size: bool) -> int:
    if not check_size and not get_settings().portal_configured:
        raise PortalUnavailableError()

    last_id = 0
    succeeded = failed = largest = 0
    while True:
        async with async_session_factory() as db:
            query = select(User.id).where(User.id > last_id).order_by(User.id).limit(100)
            account_ids = list(await db.scalars(query))
        if not account_ids:
            break

        for account_id in account_ids:
            async with async_session_factory() as db:
                service = PortalSyncService(db)
                try:
                    if check_size:
                        user = await UserService(db).get_by_id(account_id)
                        body = encode_snapshot(await service.snapshot(user))
                        largest = max(largest, len(body))
                    else:
                        await service.sync(account_id)
                except PortalSyncError as error:
                    print(f"Account {account_id}: {error.message}")
                    failed += 1
                else:
                    succeeded += 1
        last_id = account_ids[-1]

    print(f"Portal {'size check' if check_size else 'backfill'}: {succeeded} succeeded, {failed} failed")
    if check_size:
        print(f"Largest valid request: {largest} bytes")
    return int(failed > 0)


async def verify(account_id: int) -> int:
    async with async_session_factory() as db:
        user = await UserService(db).get_by_id(account_id)
        metadata = await PortalClient().get(account_id)
    if metadata is None:
        print(f"Account {account_id} is missing in Portal")
        return 1
    fields = ("first_name", "last_name", "portal_allowed", "max_portal_devices")
    matches = all(getattr(metadata, field) == getattr(user, field) for field in fields)
    print(f"Account {account_id} metadata {'matches' if matches else 'differs'}")
    return int(not matches)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-size", action="store_true", help="Generate and measure requests without sending them")
    modes.add_argument("--verify-account", type=int, help="Compare a Portal account's stored metadata")
    args = parser.parse_args()
    try:
        if args.verify_account is not None:
            return asyncio.run(verify(args.verify_account))
        return asyncio.run(backfill(check_size=args.check_size))
    except (NotFoundError, PortalUnavailableError, PortalSyncError) as error:
        print(error.message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
