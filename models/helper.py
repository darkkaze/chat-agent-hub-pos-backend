import random
import string
from typing import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os


def id_generator(prefix: str, n: int) -> Callable[[], str]:
    """
    Generates a callable that returns unique IDs with format {prefix}_{n_chars_random}.

    Random characters exclude visually confusing characters:
    - Excludes: 0, O, 1, l, I
    - Only includes: 23456789abcdefghjkmnpqrstuvwxyz

    Args:
        prefix: ID prefix (e.g. 'user', 'agent')
        n: Number of random characters

    Returns:
        Function that generates IDs with format {prefix}_{random_chars}
    """
    safe_chars = '23456789abcdefghjkmnpqrstuvwxyz'

    def generate_id() -> str:
        random_part = ''.join(random.choices(safe_chars, k=n))
        return f"{prefix}_{random_part}"

    return generate_id


def get_local_now() -> datetime:
    """
    Get current datetime in the configured timezone (from TZ environment variable).

    Falls back to UTC if TZ is not set or invalid.
    This ensures all timestamps are stored in the application's local timezone.
    """
    tz_name = os.getenv('TZ', 'UTC')
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        # Fallback to UTC if timezone is invalid
        tz = ZoneInfo('UTC')

    return datetime.now(tz)


def convert_utc_to_local(dt: datetime) -> datetime:
    """
    Convert a UTC datetime to the configured local timezone.

    Args:
        dt: UTC datetime object (should have timezone.utc)

    Returns:
        datetime object in the configured local timezone
    """
    if dt is None:
        return None

    tz_name = os.getenv('TZ', 'UTC')
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        # Fallback to UTC if timezone is invalid
        tz = ZoneInfo('UTC')

    # If dt is naive (no timezone info), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to target timezone
    return dt.astimezone(tz)