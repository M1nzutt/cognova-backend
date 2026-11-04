from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.study_challenge_write import StudyChallengeWrite
from app.schemas.study_plan_write import StudyPlanWrite


def plan_write(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "name": "  Semana de cálculo  ",
        "objective": "Preparar el parcial",
        "start_at": "2030-01-07T00:00:00Z",
        "end_at": "2030-01-14T00:00:00Z",
        "subject_ids": [3],
        "activity_ids": [8],
        "study_session_ids": [11],
    }
    value.update(overrides)
    return value


def challenge_write(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "subject_id": 3,
        "activity_id": 8,
        "title": "  Resolver ejercicios  ",
        "description": "Completar cinco problemas de práctica.",
        "target_type": "activity_completion",
        "target_value": {"status": "completed"},
        "generation_criteria": {"rationale": "Parcial en siete días"},
    }
    value.update(overrides)
    return value


def test_plan_schema_normalizes_text_and_rejects_duplicate_or_invalid_dates():
    value = StudyPlanWrite.model_validate(plan_write())

    assert value.name == "Semana de cálculo"
    assert value.subject_ids == [3]
    assert StudyPlanWrite.model_validate(plan_write(subject_ids=[])).subject_ids == []
    with pytest.raises(ValidationError):
        StudyPlanWrite.model_validate(plan_write(activity_ids=[8, 8]))
    with pytest.raises(ValidationError):
        StudyPlanWrite.model_validate(plan_write(end_at="2030-01-07T00:00:00Z"))


@pytest.mark.parametrize(
    ("target_type", "target_value", "resources"),
    [
        ("study_minutes", {"minutes": 50}, {"study_session_id": 11}),
        (
            "session_completion",
            {"lifecycle": "finished"},
            {"study_session_id": 11},
        ),
        (
            "subject_mastery",
            {"criterion": "resolver sin apuntes", "threshold": 80},
            {"subject_id": 3},
        ),
        ("custom", {"evidence": "quiz"}, {}),
    ],
)
def test_challenge_schema_accepts_structured_contextual_targets(
    target_type: str, target_value: dict[str, object], resources: dict[str, int]
):
    value = StudyChallengeWrite.model_validate(
        challenge_write(
            activity_id=None,
            target_type=target_type,
            target_value=target_value,
            **resources,
        )
    )

    assert value.target_type == target_type


def test_challenge_schema_rejects_incompatible_targets_and_bad_dates():
    with pytest.raises(ValidationError):
        StudyChallengeWrite.model_validate(
            challenge_write(target_value={"status": "pending"})
        )
    with pytest.raises(ValidationError):
        StudyChallengeWrite.model_validate(
            challenge_write(
                start_at=datetime(2030, 1, 8, tzinfo=timezone.utc),
                deadline=datetime(2030, 1, 7, tzinfo=timezone.utc),
            )
        )
    with pytest.raises(ValidationError):
        StudyChallengeWrite.model_validate(challenge_write(generation_criteria={}))
