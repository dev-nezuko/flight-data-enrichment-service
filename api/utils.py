from datetime import UTC, datetime


def make_aware(dt: datetime) -> datetime:
    """Return dt in UTC; naive values are taken to already be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
