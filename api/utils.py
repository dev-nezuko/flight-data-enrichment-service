from datetime import datetime,timezone

def make_aware(dt: datetime):
    if dt.tzinfo is None:
        return dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)