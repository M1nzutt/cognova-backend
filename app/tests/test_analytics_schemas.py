from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.analytics.cursors import decode_timeline_cursor, encode_timeline_cursor
from app.analytics.search_cursors import decode_search_cursor, encode_search_cursor
from app.analytics.structures.entries import TimelineEvent
from app.core.domain_error import DomainError
from app.schemas.analytics_search_filters import AnalyticsSearchFilters
from app.schemas.analytics_study_time_filters import AnalyticsStudyTimeFilters
from app.schemas.analytics_timeline_filters import AnalyticsTimelineFilters


def test_time_filters_require_aware_bounded_range_and_valid_timezone():
    valid = {
        "from": "2030-01-01T00:00:00-05:00",
        "to": "2030-01-02T00:00:00-05:00",
        "timezone": "America/Bogota",
    }
    filters = AnalyticsStudyTimeFilters.model_validate(valid)
    assert filters.from_at.utcoffset() is not None
    with pytest.raises(ValidationError):
        AnalyticsStudyTimeFilters.model_validate(
            {**valid, "from": "2030-01-01T00:00:00"}
        )
    with pytest.raises(ValidationError):
        AnalyticsStudyTimeFilters.model_validate(
            {**valid, "timezone": "Not/A_Timezone"}
        )
    with pytest.raises(ValidationError):
        AnalyticsStudyTimeFilters.model_validate(
            {**valid, "to": "2031-01-03T00:00:00-05:00"}
        )
    with pytest.raises(ValidationError):
        AnalyticsStudyTimeFilters.model_validate({**valid, "user_id": 12})


def test_search_filters_trim_prefix_and_reject_blank_or_unknown_fields():
    filters = AnalyticsSearchFilters.model_validate({"prefix": "  Física  "})
    assert filters.prefix == "Física"
    for value in (" ", "", "x" * 65):
        with pytest.raises(ValidationError):
            AnalyticsSearchFilters.model_validate({"prefix": value})
    with pytest.raises(ValidationError):
        AnalyticsSearchFilters.model_validate({"prefix": "abc", "user_id": 5})


def test_timeline_filters_enforce_range_and_page_limits():
    with pytest.raises(ValidationError):
        AnalyticsTimelineFilters.model_validate(
            {
                "from": "2030-01-01T00:00:00Z",
                "to": "2030-01-02T00:00:00Z",
                "limit": 101,
            }
        )
    with pytest.raises(ValidationError):
        AnalyticsTimelineFilters.model_validate(
            {
                "from": "2020-01-01T00:00:00Z",
                "to": "2040-01-01T00:00:00Z",
            }
        )


def test_cursors_roundtrip_and_bind_to_filter_values():
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    end = datetime(2030, 1, 3, tzinfo=timezone.utc)
    event = TimelineEvent(start, "activity", "activity", 4, 2, "deadline_changed")
    cursor = encode_timeline_cursor(event, start, end, None)
    assert decode_timeline_cursor(cursor, start, end, None) == event.key
    with pytest.raises(DomainError):
        decode_timeline_cursor(cursor, start, end, "activity")
    search_cursor = encode_search_cursor(("fisica", "subject", 2), "Física", None)
    assert decode_search_cursor(search_cursor, "fisica", None) == (
        "fisica",
        "subject",
        2,
    )
    with pytest.raises(DomainError):
        decode_search_cursor(search_cursor, "matemática", None)
    with pytest.raises(DomainError):
        decode_search_cursor("not a cursor", "fisica", None)
