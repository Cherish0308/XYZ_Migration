from __future__ import annotations

from datetime import datetime, date


def parse_date(value: str) -> date:
    
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def parse_timestamp(value: str) -> datetime:
    
    try:
        # Handle trailing Z by converting to +00:00
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        # Fallback to simple "YYYY-MM-DD HH:MM:SS"
        return datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")


def normalize_period(value: str) -> str:
    
    if len(value) >= 7 and value[4] == "-":
        return value[:7]
    raise ValueError(f"Invalid period: {value}")
