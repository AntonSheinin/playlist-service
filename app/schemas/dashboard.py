from datetime import datetime

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Dashboard statistics."""

    channels_total: int
    channels_synced: int
    channels_orphaned: int
    groups: int
    packages: int
    tariffs: int
    users: int
    users_enabled: int
    users_disabled: int
    last_sync: datetime | None
