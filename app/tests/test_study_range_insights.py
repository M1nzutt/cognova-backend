from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.structures.study_range_insights import (
    StudyInterval,
    StudyRangeInsights,
)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 1, 1, hour, minute, tzinfo=timezone.utc)


def test_range_totals_clip_intervals_and_count_distinct_sessions():
    index = StudyRangeInsights(
        [
            StudyInterval(1, 10, at(9), at(10)),
            StudyInterval(1, 10, at(10), at(10, 30)),
            StudyInterval(2, 10, at(10, 15), at(11)),
            StudyInterval(3, 20, at(9, 30), at(10)),
        ]
    )

    totals = index.between(at(10), at(10, 45))

    assert totals[10].duration_microseconds == 60 * 60 * 1_000_000
    assert totals[10].session_count == 2
    assert totals[20].duration_microseconds == 0
    assert totals[20].session_count == 0


def test_range_totals_respect_half_open_boundaries_and_empty_index():
    index = StudyRangeInsights([StudyInterval(1, 10, at(9), at(10))])
    assert index.between(at(10), at(11))[10].duration_microseconds == 0
    assert StudyRangeInsights().between(at(9), at(11)) == {}
    with pytest.raises(ValueError):
        index.between(at(11), at(10))


def test_range_index_rejects_naive_or_invalid_intervals():
    naive = datetime(2030, 1, 1)
    with pytest.raises(ValueError):
        StudyRangeInsights([StudyInterval(1, 10, naive, at(10))])
    with pytest.raises(ValueError):
        StudyRangeInsights([StudyInterval(1, 10, at(10), at(9))])
    with pytest.raises(ValueError):
        StudyRangeInsights().between(naive, at(10))


def test_range_index_handles_microsecond_precision():
    start = at(9)
    end = start + timedelta(microseconds=7)
    totals = StudyRangeInsights([StudyInterval(1, 10, start, end)]).between(
        start + timedelta(microseconds=2), end
    )
    assert totals[10].duration_microseconds == 5
