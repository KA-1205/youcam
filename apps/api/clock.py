"""Single clock seam; tests may inject a fake to advance time deterministically."""
from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """SQLite round-trips timezone-aware columns as naive; treat stored values as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
