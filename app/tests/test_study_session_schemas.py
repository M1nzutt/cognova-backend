from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.domain_error import DomainError
from app.schemas.study_session_filters import StudySessionFilters
from app.schemas.study_session_finish import StudySessionFinish
from app.schemas.study_session_write import StudySessionWrite
from app.study_sessions.timer import elapsed_seconds, strictly_after
from app.study_sessions.transitions import (
    require_finish,
    require_pause,
    require_planned,
    require_resume,
    require_start,
)

START = "2030-01-02T03:04:05Z"
PLAN = {
    "subject_id": 1,
    "activity_id": None,
    "planned_start_at": START,
    "planned_duration": 10,
}


@pytest.mark.parametrize("duration", [10, 180])
def test_planned_duration_boundaries(duration):
    assert (
        StudySessionWrite(**{**PLAN, "planned_duration": duration}).planned_duration
        == duration
    )


@pytest.mark.parametrize(
    "override",
    [
        {"planned_duration": 9},
        {"planned_duration": 181},
        {"planned_duration": True},
        {"planned_duration": 10.0},
        {"subject_id": 0},
        {"subject_id": True},
        {"planned_start_at": "2030-01-02T03:04:05"},
        {"planned_start_at": "2030-01-02"},
        {"user_id": 1},
        {"start_at": START},
    ],
)
def test_planning_rejects_invalid_or_server_owned_fields(override):
    with pytest.raises(ValidationError):
        StudySessionWrite(**{**PLAN, **override})


def test_activity_is_optional_and_aware_offset_is_preserved():
    planned = StudySessionWrite(
        **{**PLAN, "activity_id": 5, "planned_start_at": "2030-01-02T00:04:05-03:00"}
    )
    assert planned.activity_id == 5
    assert planned.planned_start_at.utcoffset() == timedelta(hours=-3)


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "done"},
        {"status": "completed", "context": "other"},
        {"status": "partial", "other_text": "incorrect"},
        {"status": "cancelled", "context": "invalid"},
    ],
)
def test_finish_request_rejects_invalid_result_or_context(payload):
    with pytest.raises(ValidationError):
        StudySessionFinish(**payload)


def test_other_context_requires_trimmed_nonblank_text_and_caps_length():
    result = StudySessionFinish(
        status="partial", context="other", other_text="  Cambié de tarea  "
    )
    assert result.other_text == "Cambié de tarea"
    with pytest.raises(ValidationError):
        StudySessionFinish(status="partial", context="other")
    with pytest.raises(ValidationError):
        StudySessionFinish(status="partial", context="other", other_text="  ")
    with pytest.raises(ValidationError):
        StudySessionFinish(status="partial", context="other", other_text="x" * 201)


def test_filters_validate_range_and_cursor_pair():
    assert StudySessionFilters(limit="2").limit == 2
    assert (
        StudySessionFilters(
            planned_start_from=START,
            planned_start_to="2030-01-03T00:00:00Z",
            after_planned_start_at=START,
            after_id=2,
        ).after_id
        == 2
    )
    for params in (
        {"planned_start_from": START, "planned_start_to": START},
        {"after_id": 2},
        {"after_planned_start_at": START},
        {"limit": True},
    ):
        with pytest.raises(ValidationError):
            StudySessionFilters(**params)


def test_transition_guards_reject_double_actions_and_terminal_state():
    require_planned("planned")
    require_start("planned")
    require_pause("running")
    require_resume("paused")
    require_finish("planned", "postponed")
    require_finish("running", "completed")
    require_finish("paused", "cancelled")
    for operation, args in (
        (require_planned, ("running",)),
        (require_start, ("paused",)),
        (require_pause, ("paused",)),
        (require_resume, ("running",)),
        (require_finish, ("planned", "completed")),
        (require_finish, ("finished", "completed")),
    ):
        with pytest.raises(DomainError):
            operation(*args)


def test_elapsed_duration_sums_closed_windows_and_excludes_pause():
    first = datetime(2030, 1, 1, tzinfo=timezone.utc)
    intervals = [
        (first, first + timedelta(seconds=12, microseconds=250000)),
        (first + timedelta(hours=1), first + timedelta(hours=1, seconds=7)),
        (first + timedelta(hours=2), None),
    ]
    assert elapsed_seconds(intervals) == Decimal("19.250000")


def test_elapsed_duration_normalizes_timezone_offsets():
    start = datetime.fromisoformat("2030-01-01T10:00:00-05:00")
    end = datetime.fromisoformat("2030-01-01T15:00:01.123456+00:00")
    assert elapsed_seconds([(start, end)]) == Decimal("1.123456")


def test_timer_never_returns_nonpositive_interval():
    at = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert strictly_after(at, at) == at + timedelta(microseconds=1)
    with pytest.raises(ValueError):
        strictly_after(datetime(2030, 1, 1), at)
