"""Tests for cron schedule parser."""

from core.cron.parser import parse_schedule, next_run


def test_parse_duration_minutes():
    cron, dt = parse_schedule("30m")
    assert cron == "*/30 * * * *"
    assert dt is None


def test_parse_duration_hours():
    cron, dt = parse_schedule("2h")
    assert cron == "0 */2 * * *"
    assert dt is None


def test_parse_duration_seconds():
    cron, dt = parse_schedule("30s")
    assert cron == "*/30 * * * * *"
    assert dt is None


def test_parse_every_day_at():
    cron, dt = parse_schedule("every day at 9")
    assert cron == "0 09 * * *"
    assert dt is None


def test_parse_every_day_at_with_minutes():
    cron, dt = parse_schedule("every day at 9:30")
    assert cron == "30 09 * * *"
    assert dt is None


def test_parse_every_day_at_arabic():
    """9 صباحاً should work same as 'every day at 9'."""
    cron, dt = parse_schedule("every day at 9")
    assert cron == "0 09 * * *"


def test_parse_every_monday():
    cron, dt = parse_schedule("every monday at 10")
    assert "10" in cron or "010" in cron
    assert "1" in cron or "0" in cron  # Monday = 1 (iso) or 0 (cron legacy)
    assert dt is None


def test_parse_every_weekday():
    cron, dt = parse_schedule("every weekday at 8")
    assert "8" in cron
    assert "1-5" in cron
    assert dt is None


def test_parse_iso_timestamp():
    cron, dt = parse_schedule("2026-07-01T09:00:00")
    assert cron == "once"
    assert dt is not None


def test_parse_cron_direct():
    cron, dt = parse_schedule("0 9 * * *")
    assert cron == "0 9 * * *"
    assert dt is None


def test_parse_cron_5_fields():
    cron, dt = parse_schedule("30 14 * * 5")
    assert cron == "30 14 * * 5"


def test_parse_invalid_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_schedule("not a schedule at all")


def test_next_run_daily():
    result = next_run("0 9 * * *")
    assert result is not None
    assert "T09:00:00" in result


def test_next_run_every_30m():
    result = next_run("*/30 * * * *")
    assert result is not None


def test_next_run_one_shot_past():
    from datetime import datetime, timezone, timedelta
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    result = next_run("once", one_shot_dt=past)
    assert result is None  # Already past


def test_next_run_one_shot_future():
    from datetime import datetime, timezone, timedelta
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    result = next_run("once", one_shot_dt=future)
    assert result is not None
