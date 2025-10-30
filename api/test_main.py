"""Pure validation checks; no broker, database or provider calls."""

import os
import time
from datetime import UTC, datetime, timedelta, timezone

import pytest

from api.utils import make_aware


@pytest.fixture
def host_timezone_ahead_of_utc():
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "Asia/Karachi"
    time.tzset()
    yield
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


def test_naive_timestamp_is_assumed_utc():
    value = datetime(2027, 1, 1)
    assert make_aware(value) == datetime(2027, 1, 1, tzinfo=UTC)


def test_naive_timestamp_ignores_host_timezone(host_timezone_ahead_of_utc):
    assert make_aware(datetime(2027, 1, 1, 10)) == datetime(2027, 1, 1, 10, tzinfo=UTC)


def test_offset_timestamp_is_normalized_to_utc():
    value = datetime(2027, 1, 1, 3, tzinfo=timezone(timedelta(hours=3)))
    assert make_aware(value) == datetime(2027, 1, 1, tzinfo=UTC)
    assert make_aware(value).tzinfo == UTC
