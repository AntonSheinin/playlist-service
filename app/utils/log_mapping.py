"""Mapping and sorting utilities for Auth Service session/access-log responses."""

from datetime import datetime, timezone
from typing import Any

ACCESS_LOG_SORT_FIELDS = {"accessed_at", "ip", "channel", "action"}
SESSION_LOG_SORT_FIELDS = {"started_at", "ended_at", "duration", "ip", "channel"}


def normalize_sort_dir(sort_dir: str) -> str:
    return "asc" if sort_dir and sort_dir.lower() == "asc" else "desc"


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    candidate = value.replace("Z", "+00:00", 1)
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def sort_items(
    items: list[dict[str, Any]],
    sort_by: str,
    sort_dir: str,
    date_fields: set[str],
) -> list[dict[str, Any]]:
    if not items:
        return items

    with_value: list[tuple[Any, dict[str, Any]]] = []
    without_value: list[dict[str, Any]] = []

    for item in items:
        value = item.get(sort_by)
        if value is None:
            without_value.append(item)
            continue
        if sort_by in date_fields and isinstance(value, str):
            parsed = parse_datetime(value)
            value = normalize_datetime(parsed) if parsed else value
        with_value.append((value, item))

    with_value.sort(key=lambda pair: pair[0], reverse=sort_dir == "desc")
    return [item for _, item in with_value] + without_value


def map_access_log_entry(log: dict[str, Any]) -> dict[str, Any]:
    result = log.get("result")
    reason = log.get("reason")
    if not result:
        action = "-"
    elif reason:
        action = f"{result}: {reason}"
    else:
        action = result

    return {
        "accessed_at": log.get("timestamp"),
        "ip": log.get("client_ip"),
        "channel": log.get("stream_name"),
        "action": action,
        "user_agent": log.get("protocol"),
    }


def map_session_log_entry(log: dict[str, Any]) -> dict[str, Any]:
    started_at = log.get("started_at")
    duration = None
    if isinstance(started_at, str):
        started_dt = normalize_datetime(parse_datetime(started_at))
    elif isinstance(started_at, datetime):
        started_dt = normalize_datetime(started_at)
    else:
        started_dt = None
    if started_dt:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        duration = max(0, int((now - started_dt).total_seconds()))

    return {
        "started_at": started_at,
        "ended_at": None,
        "duration": duration,
        "ip": log.get("client_ip"),
        "channel": log.get("stream_name"),
        "user_agent": log.get("protocol"),
    }
