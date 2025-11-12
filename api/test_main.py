"""Pure validation checks; no broker, database or provider calls."""
from datetime import datetime, timezone, timedelta
from api.utils import make_aware


def test_naive_timestamp_is_assumed_utc():
    value = datetime(2027, 1, 1)
    assert make_aware(value).tzinfo == timezone.utc


def test_offset_timestamp_is_normalized_to_utc():
    value = datetime(2027, 1, 1, 3, tzinfo=timezone(timedelta(hours=3)))
    assert make_aware(value) == datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert make_aware(value).tzinfo == timezone.utc
