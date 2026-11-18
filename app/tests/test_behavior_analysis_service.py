from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.behavior_analysis_service import BehaviorAnalysisService


def session(identifier, result, *, lifecycle="finished", actual="60.140789"):
    return SimpleNamespace(
        id=identifier,
        subject_id=1,
        activity_id=2,
        planned_duration=10,
        actual_duration=Decimal(actual),
        execution_state=lifecycle,
        status=result,
        planned_start_at=datetime(2030, 1, identifier, 12, tzinfo=timezone.utc),
    )


def context(rows):
    return SimpleNamespace(
        sessions=rows,
        subjects=[SimpleNamespace(id=1, name="Biología")],
        activities=[SimpleNamespace(id=2, title="Repasar células")],
    )


def analyze(monkeypatch, rows, *, completed=1, reviewed=5):
    monkeypatch.setattr(
        "app.services.behavior_analysis_service.AcademicContext",
        lambda _db, _user_id: context(rows),
    )
    db = SimpleNamespace(scalar=Mock(side_effect=[completed, reviewed]))
    return BehaviorAnalysisService(db).analyze(99)


def test_five_short_session_records_are_described_without_claiming_a_habit(monkeypatch):
    rows = [
        session(1, "completed"),
        *(session(identifier, "partial") for identifier in range(2, 6)),
    ]

    response = analyze(monkeypatch, rows)

    assert response.completed_session_count == 1
    assert response.reviewed_session_count == 5
    assert response.state == "factual_summary"
    observation = response.observations[0]
    assert observation.observation == (
        "En 5 de 5 registros se registró cerca de 1 min frente a 10 min planificados."
    )
    assert "ni permiten concluir que sea un hábito" in observation.interpretation
    assert "¿" == observation.question[0]
    assert observation.evidence[0].planned_minutes == 10
    assert observation.evidence[0].actual_seconds == "60.140789"
    assert observation.evidence[0].summary == (
        "Biología · Repasar células: 10 min planificados"
    )
    assert len(observation.related_resources) == 7
    assert (
        len([item for item in observation.related_resources if item.kind == "subject"])
        == 1
    )


def test_partial_cancelled_and_incomplete_sessions_are_not_counted_as_completed(
    monkeypatch,
):
    rows = [
        session(1, "partial"),
        session(2, "cancelled", actual="0"),
        session(3, None, lifecycle="running"),
        session(4, None, lifecycle="planned", actual="0"),
    ]

    response = analyze(monkeypatch, rows, completed=0, reviewed=1)

    assert response.completed_session_count == 0
    assert response.reviewed_session_count == 1
    assert response.observations[0].evidence[0].result == "partial"


def test_subsecond_timer_variation_does_not_mark_a_planned_ten_minutes_as_different(
    monkeypatch,
):
    rows = [
        *(session(identifier, "partial") for identifier in range(1, 5)),
        session(5, "completed", actual="600.232317"),
    ]

    response = analyze(monkeypatch, rows)

    assert response.observations[0].observation == (
        "En 4 de 5 registros se registró cerca de 1 min frente a 10 min planificados."
    )
    assert response.observations[0].evidence[-1].actual_seconds == "600.232317"


def test_only_cancelled_or_incomplete_records_produce_an_informative_empty_state(
    monkeypatch,
):
    rows = [
        session(1, "cancelled", actual="0"),
        session(2, None, lifecycle="running"),
        session(3, None, lifecycle="planned", actual="0"),
    ]

    response = analyze(monkeypatch, rows, completed=0, reviewed=0)

    assert response.state == "insufficient_data"
    assert response.observations == []
