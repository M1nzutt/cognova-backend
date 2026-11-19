from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.academic_intelligence.gemini_schemas import BehaviorInsight
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
    assert observation.conclusion == observation.observation
    assert "puede ser relevante" in observation.interpretation
    assert "no indican por qué ocurrió" in observation.uncertainty
    assert observation.suggestion.startswith("Si fueron sesiones de estudio reales,")
    assert observation.interpretation_source == "factual_fallback"
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
    assert "sesiones finalizadas con duración registrada" in (
        response.insufficient_data_guidance
    )


def test_grounded_gemini_insight_and_cached_result(monkeypatch):
    rows = [
        session(1, "completed", actual="600"),
        *(session(identifier, "partial") for identifier in range(2, 6)),
    ]
    generator = Mock(
        return_value=BehaviorInsight(
            interpretation=(
                "Comparar ambos tiempos puede ayudar a valorar el tamaño de los "
                "bloques previstos."
            ),
            suggestion=(
                "Si fueron sesiones de estudio reales, podrías probar un bloque "
                "más breve y revisar si se ajusta mejor."
            ),
        )
    )
    monkeypatch.setattr(
        "app.services.behavior_analysis_service.AcademicContext",
        lambda _db, _user_id: context(rows),
    )
    db = SimpleNamespace(scalar=Mock(side_effect=[1, 5, 1, 5]))
    service = BehaviorAnalysisService(db, generator)

    first = service.analyze(93001)
    second = service.analyze(93001)

    assert first.observations[0].interpretation_source == "gemini"
    assert first.observations[0].suggestion.startswith(
        "Si fueron sesiones de estudio reales,"
    )
    assert second.observations[0].interpretation == first.observations[0].interpretation
    generator.assert_called_once()


def test_gemini_failure_uses_factual_conclusion_and_safe_suggestion(monkeypatch):
    rows = [
        session(1, "completed", actual="600"),
        *(session(identifier, "partial") for identifier in range(2, 6)),
    ]
    generator = Mock(side_effect=RuntimeError("provider unavailable"))
    monkeypatch.setattr(
        "app.services.behavior_analysis_service.AcademicContext",
        lambda _db, _user_id: context(rows),
    )
    db = SimpleNamespace(scalar=Mock(side_effect=[1, 5]))

    response = BehaviorAnalysisService(db, generator).analyze(93002)

    observation = response.observations[0]
    assert observation.conclusion == (
        "En 4 de 5 registros se registró cerca de 1 min frente a 10 min planificados."
    )
    assert observation.interpretation_source == "factual_fallback"
    assert observation.uncertainty
    assert observation.suggestion.startswith("Si fueron sesiones de estudio reales,")


def test_insufficient_evidence_does_not_call_gemini(monkeypatch):
    rows = [session(1, "partial")]
    generator = Mock()
    monkeypatch.setattr(
        "app.services.behavior_analysis_service.AcademicContext",
        lambda _db, _user_id: context(rows),
    )
    db = SimpleNamespace(scalar=Mock(side_effect=[0, 1]))

    response = BehaviorAnalysisService(db, generator).analyze(93003)

    assert response.observations[0].interpretation_source == "factual_fallback"
    generator.assert_not_called()


def test_unsafe_or_unsupported_gemini_claims_are_replaced_with_factual_guidance(
    monkeypatch,
):
    rows = [
        session(1, "completed", actual="600"),
        *(session(identifier, "partial") for identifier in range(2, 6)),
    ]
    generator = Mock(
        return_value=BehaviorInsight(
            interpretation="La motivación explica que hayas terminado antes.",
            suggestion=(
                "Si fueron sesiones de estudio reales, intenta estudiar 25 minutos."
            ),
        )
    )
    monkeypatch.setattr(
        "app.services.behavior_analysis_service.AcademicContext",
        lambda _db, _user_id: context(rows),
    )
    db = SimpleNamespace(scalar=Mock(side_effect=[1, 5]))

    response = BehaviorAnalysisService(db, generator).analyze(93004)

    observation = response.observations[0]
    assert observation.interpretation_source == "factual_fallback"
    assert "motivación" not in observation.interpretation
    assert "25 minutos" not in observation.suggestion
