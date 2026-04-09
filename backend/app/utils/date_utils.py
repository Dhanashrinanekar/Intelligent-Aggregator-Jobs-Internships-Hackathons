"""
Date Utilities for Job Aggregator
Handles application_start_date and application_end_date logic consistently
across all scrapers.

Rules:
    - application_start_date: use API-provided start date if available,
      otherwise fall back to posted_date (i.e., the scraping timestamp).
    - application_end_date: use API-provided expiry date (validThrough,
      deadline, etc.) if available, otherwise posted_date + 20 days.
    - Neither field is ever NULL in the database.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


# Default validity window when no expiry date is provided by the API
DEFAULT_VALIDITY_DAYS = 20


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def parse_date(value) -> Optional[datetime]:
    """
    Try to coerce *value* into a timezone-aware datetime object.

    Accepts:
        - datetime objects (naive ones are assumed UTC)
        - ISO-8601 strings (with or without timezone info)
        - Common date strings: 'YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY'
        - Epoch integers / floats
        - None / empty string  → returns None

    Returns:
        datetime (timezone-aware, UTC) or None if parsing failed.
    """
    if value is None:
        return None

    # Already a datetime
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    # Numeric epoch
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    # String handling
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        # Try ISO formats (handles e.g. "2024-06-01T00:00:00+05:30")
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%B %d, %Y",    # e.g. "June 01, 2024"
            "%b %d, %Y",    # e.g. "Jun 01, 2024"
        ):
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

    return None


def resolve_dates(
    posted_date=None,
    api_start_date=None,
    api_end_date=None,
    validity_days: int = DEFAULT_VALIDITY_DAYS,
):
    """
    Resolve application_start_date and application_end_date for a job posting.

    Priority rules
    --------------
    application_start_date:
        1. Use api_start_date if parseable.
        2. Fall back to posted_date if parseable.
        3. Fall back to now (UTC).

    application_end_date:
        1. Use api_end_date if parseable AND it is in the future.
        2. Fall back to application_start_date + validity_days.

    Parameters
    ----------
    posted_date   : raw date value provided by the scraper / API
    api_start_date: explicit start date from the API (rarely available)
    api_end_date  : expiry / deadline / validThrough from the API
    validity_days : days to add when no end date is available (default 20)

    Returns
    -------
    (application_start_date, application_end_date) as timezone-aware datetimes
    """
    now = now_utc()

    # --- Resolve start date ---
    start = parse_date(api_start_date) or parse_date(posted_date) or now

    # --- Resolve end date ---
    end = parse_date(api_end_date)

    # Discard end dates that are already in the past (stale API data)
    if end is not None and end <= now:
        end = None

    if end is None:
        end = start + timedelta(days=validity_days)

    return start, end


def resolve_dates_for_job(job: dict, validity_days: int = DEFAULT_VALIDITY_DAYS) -> dict:
    """
    Convenience wrapper: accepts a job dictionary, resolves the two date
    fields in-place, and returns the same dictionary.

    The function reads the following keys (any may be absent / None):
        posted_date, scraped_at, fetched_at  → used as posted_date
        application_start_date               → used as api_start_date
        application_end_date, validThrough,
        deadline, expires_at                 → used as api_end_date

    After the call, job['application_start_date'] and
    job['application_end_date'] are always datetime objects.
    """
    # Choose the best "posted" timestamp available in the dict
    raw_posted = (
        job.get("posted_date")
        or job.get("scraped_at")
        or job.get("fetched_at")
        or job.get("updated")
    )

    # The API may already have a start date set (usually None from scrapers)
    raw_start = job.get("application_start_date")

    # Possible expiry field names used across different APIs
    raw_end = (
        job.get("application_end_date")
        or job.get("validThrough")
        or job.get("deadline")
        or job.get("expires_at")
        or job.get("deadline_str")
    )

    start, end = resolve_dates(
        posted_date=raw_posted,
        api_start_date=raw_start,
        api_end_date=raw_end,
        validity_days=validity_days,
    )

    job["application_start_date"] = start
    job["application_end_date"] = end
    return job