"""Parse human-readable schedules into cron expressions."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional


def parse_schedule(text: str) -> tuple[str, Optional[datetime]]:
    """Parse a schedule string into (cron_expression, one_shot_datetime).

    Returns:
        (cron_expression, None) for recurring jobs
        ("once", datetime) for one-shot jobs
    """
    text = text.strip().lower()

    # ISO timestamp -> one-shot
    try:
        dt = datetime.fromisoformat(text)
        return ("once", dt)
    except (ValueError, TypeError):
        pass

    # Duration: "30m", "2h", "90s"
    m = re.match(r"^(\d+)\s*(m|min|h|hr|s|sec)$", text)
    if m:
        value = int(m.group(1))
        unit = m.group(2)
        if unit in ("s", "sec"):
            return (f"*/{value} * * * * *", None)
        elif unit in ("m", "min"):
            return (f"*/{value} * * * *", None)
        elif unit in ("h", "hr"):
            return (f"0 */{value} * * *", None)

    # "every X minutes/hours/days"
    m = re.match(r"every\s+(\d+)\s*(m|min|h|hr|day|d)", text)
    if m:
        value = int(m.group(1))
        unit = m.group(2)
        if unit in ("m", "min"):
            return (f"*/{value} * * * *", None)
        elif unit in ("h", "hr"):
            return (f"0 */{value} * * *", None)
        elif unit in ("day", "d"):
            return (f"0 0 */{value} * *", None)

    # "every day at HH:MM" or "every day at H"
    m = re.match(r"every\s+day\s+at\s+(\d{1,2})(?::(\d{2}))?", text)
    if m:
        hour = m.group(1).zfill(2)
        minute = m.group(2) or "0"
        return (f"{minute} {hour} * * *", None)

    # "every weekday at HH:MM"
    m = re.match(r"every\s+weekday\s+at\s+(\d{1,2})(?::(\d{2}))?", text)
    if m:
        hour = m.group(1).zfill(2)
        minute = m.group(2) or "0"
        return (f"{minute} {hour} * * 1-5", None)

    # "every monday/tuesday/... at HH:MM"
    day_map = {
        "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
        "thursday": 4, "friday": 5, "saturday": 6,
        "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
    }
    for name, num in day_map.items():
        pattern = rf"every\s+{name}\s+at\s+(\d{{1,2}})(?::(\d{{2}}))?"
        m = re.match(pattern, text)
        if m:
            hour = m.group(1).zfill(2)
            minute = m.group(2) or "0"
            return (f"{minute} {hour} * * {num}", None)

    # Already a cron expression (5 fields with valid values)
    cron_parts = text.split()
    if len(cron_parts) == 5:
        # Validate each field is a number, * , */, or comma-separated
        valid_field = re.compile(r'^(\d+|\*|\*\/\d+|\d+-\d+|\d+(?:,\d+)*)$')
        if all(valid_field.match(p) for p in cron_parts):
            return (text, None)

    raise ValueError(f"Unrecognized schedule: {text!r}")


def next_cron_run(cron_expr: str) -> Optional[str]:
    """Calculate next run time from a cron expression (simplified).

    Returns ISO datetime string or None if can't compute.
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return None

    minute_field, hour_field, dom_field, month_field, dow_field = parts
    now = datetime.now(timezone.utc)

    # "every N minutes"
    if minute_field.startswith("*/"):
        interval = int(minute_field[2:])
        next_minute = ((now.minute // interval) + 1) * interval
        if next_minute >= 60:
            next_dt = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
        else:
            next_dt = now.replace(minute=next_minute, second=0, microsecond=0)
        return next_dt.isoformat()

    # "every N hours"
    if hour_field.startswith("*/") and minute_field == "0":
        interval = int(hour_field[2:])
        next_hour = ((now.hour // interval) + 1) * interval
        if next_hour >= 24:
            next_dt = now.replace(day=now.day + 1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_dt = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        return next_dt.isoformat()

    # Daily at specific time
    if dom_field == "*" and month_field == "*" and dow_field == "*":
        try:
            hour = int(hour_field)
            minute = int(minute_field)
            next_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_dt <= now:
                next_dt = next_dt.replace(day=next_dt.day + 1)
            return next_dt.isoformat()
        except (ValueError, OverflowError):
            pass

    return (now + timedelta(minutes=1)).isoformat()


def next_run(schedule: str, one_shot_dt: Optional[datetime] = None) -> Optional[str]:
    """Calculate the next run time for a schedule."""
    if one_shot_dt:
        if one_shot_dt < datetime.now(timezone.utc):
            return None
        return one_shot_dt.isoformat()
    return next_cron_run(schedule)
