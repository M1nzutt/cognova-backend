from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def strictly_after(instant: datetime, lower_bound: datetime) -> datetime:
    if instant.tzinfo is None or lower_bound.tzinfo is None:
        raise ValueError("Timer timestamps must be timezone-aware")
    if instant <= lower_bound:
        return lower_bound + timedelta(microseconds=1)
    return instant


def elapsed_seconds(
    intervals: Iterable[tuple[datetime, datetime | None]],
) -> Decimal:
    """Sum closed execution windows exactly; open windows count after closing."""
    total_microseconds = 0
    for started_at, ended_at in intervals:
        if ended_at is None:
            continue
        if started_at.tzinfo is None or ended_at.tzinfo is None:
            raise ValueError("Interval timestamps must be timezone-aware")
        delta = ended_at - started_at
        if delta <= timedelta(0):
            raise ValueError("Closed intervals must have positive duration")
        total_microseconds += (
            delta.days * 86400 + delta.seconds
        ) * 1_000_000 + delta.microseconds
    return Decimal(total_microseconds).scaleb(-6)
