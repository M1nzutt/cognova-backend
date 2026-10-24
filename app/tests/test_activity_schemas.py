import pytest
from pydantic import ValidationError

from app.activities.transitions import validate_transition
from app.core.domain_error import DomainError
from app.schemas.activity_filters import ActivityFilters
from app.schemas.activity_write import ActivityWrite

PAYLOAD = dict(
    title="Ensayo",
    subject_id=1,
    deadline="2030-01-01T12:00:00Z",
    priority="medium",
    status="pending",
    estimated_duration=30,
    notes=None,
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", " "),
        ("title", "a" * 51),
        ("title", "a\x00b"),
        ("subject_id", True),
        ("subject_id", "1"),
        ("subject_id", 0),
        ("deadline", "2030-01-01T12:00:00"),
        ("deadline", "2030-01-01"),
        ("deadline", 1893499200),
        ("deadline", "1893499200"),
        ("deadline", None),
        ("priority", "critical"),
        ("status", "done"),
        ("estimated_duration", True),
        ("estimated_duration", 9),
        ("estimated_duration", 301),
        ("estimated_duration", 10.0),
        ("notes", "a" * 201),
        ("notes", "\x00"),
        ("user_id", 1),
        ("original_deadline", "2030-01-01T12:00:00Z"),
        ("deadline_revision", 2),
    ],
)
def test_invalid_payload(field, value):
    with pytest.raises(ValidationError):
        ActivityWrite(**{**PAYLOAD, field: value})


@pytest.mark.parametrize("duration", [10, 300])
@pytest.mark.parametrize("priority", ["low", "medium", "high", "urgent"])
def test_valid_boundaries(duration, priority):
    data = ActivityWrite(
        **{
            **PAYLOAD,
            "title": " é" * 0 + "é" * 50,
            "notes": "é" * 200,
            "estimated_duration": duration,
            "priority": priority,
        }
    )
    assert len(data.title) == 50 and data.deadline.utcoffset() is not None


def test_filters_reject_reversed_range():
    with pytest.raises(ValidationError):
        ActivityFilters(
            deadline_from="2030-02-01T00:00:00Z", deadline_to="2030-01-01T00:00:00Z"
        )


@pytest.mark.parametrize(
    "current", ["pending", "in_progress", "completed", "postponed", "cancelled"]
)
@pytest.mark.parametrize(
    "target", ["pending", "in_progress", "completed", "postponed", "cancelled"]
)
def test_transition_matrix(current, target):
    if current in {"completed", "cancelled"} and target not in {current, "pending"}:
        with pytest.raises(DomainError, match="Reabre"):
            validate_transition(current, target)
    else:
        validate_transition(current, target)
