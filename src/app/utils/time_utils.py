from __future__ import annotations

from datetime import datetime, date


def parse_date(value: str) -> date:
    """
    Parse a date string (YYYY-MM-DD or ISO with time) into a date.
    We only care about the date portion.
    """
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def parse_timestamp(value: str) -> datetime:
    """
    Parse an ISO-like timestamp.

    Supports:
      - "2025-11-30T12:34:56"
      - "2025-11-30T12:34:56Z"
      - "2025-11-30 12:34:56"
    """
    try:
        # Handle trailing Z by converting to +00:00
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        # Fallback to simple "YYYY-MM-DD HH:MM:SS"
        return datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")


def normalize_period(value: str) -> str:
    """
    Normalize a period string to 'YYYY-MM'.

    If a day is present (YYYY-MM-DD), we just cut it off.
    """
    if len(value) >= 7 and value[4] == "-":
        return value[:7]
    raise ValueError(f"Invalid period: {value}")
