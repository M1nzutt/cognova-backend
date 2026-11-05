import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.academic_intelligence.academic_event import AcademicEvent
from app.academic_intelligence.academic_journey import AcademicJourney
from app.academic_intelligence.decision_route import DecisionRoute
from app.academic_intelligence.decision_trail import DecisionTrail
from app.academic_intelligence.gemini_provider import GeminiProvider
from app.academic_intelligence.gemini_schemas import (
    BehaviorObservation,
    BehaviorProposal,
    PlanProposal,
    ProposedChallenge,
)
from app.academic_intelligence.pending_analysis import PendingAnalysis
from app.academic_intelligence.pending_analysis_flow import PendingAnalysisFlow
from app.academic_intelligence.proposal_validation import validate_proposal
from app.academic_intelligence.schedule_entry import ScheduleEntry
from app.academic_intelligence.schedule_index import ScheduleIndex
from app.core.domain_error import DomainError
from app.services.behavior_analysis_service import BehaviorAnalysisService
from app.study_plans.decision_entry import DecisionEntry


def test_pending_analysis_flow_is_fifo_and_reusable():
    flow = PendingAnalysisFlow()
    flow.add(PendingAnalysis("session", 1, 2))
    flow.add(PendingAnalysis("activity", 2, 2))
    assert [flow.take().resource_id, flow.take().resource_id] == [1, 2]
    assert flow.take() is None
    assert len(flow) == 0
    flow.add(PendingAnalysis("session", 3, 2))
    assert flow.take().resource_id == 3


def test_academic_journey_keeps_chronology_and_rejects_reverse_append():
    now = datetime.now(timezone.utc)
    journey = AcademicJourney()
    journey.append(AcademicEvent(now, "activity", 1, 2))
    journey.append(AcademicEvent(now + timedelta(minutes=1), "session", 2, 2))
    assert [item.resource_id for item in journey] == [1, 2]
    with pytest.raises(ValueError):
        journey.append(AcademicEvent(now - timedelta(minutes=1), "activity", 3, 2))


def test_decision_trail_navigates_both_directions():
    trail = DecisionTrail()
    now = datetime.now(timezone.utc)
    for identifier in (1, 2, 3):
        trail.record(DecisionEntry(identifier, "edited", "name", "a", "b", now))
    assert [item.id for item in trail.forward()] == [1, 2, 3]
    assert [item.id for item in trail.backward()] == [3, 2, 1]


def test_schedule_index_balances_and_preserves_half_open_order():
    index = ScheduleIndex()
    now = datetime.now(timezone.utc)
    for identifier in range(100):
        index.add(
            ScheduleEntry(now + timedelta(minutes=identifier), "session", identifier, 1)
        )
    assert len(index) == 100
    assert index.max_depth() <= 8
    assert [
        item.resource_id
        for item in index.between(
            now + timedelta(minutes=8), now + timedelta(minutes=11)
        )
    ] == [8, 9, 10]
    with pytest.raises(ValueError):
        index.add(ScheduleEntry(now, "session", 0, 1))


def test_decision_route_evaluates_all_viability_branches():
    route = DecisionRoute()
    assert (
        route.evaluate(has_resources=False, valid_dates=True, enough_context=True)
        == "insufficient_evidence"
    )
    assert (
        route.evaluate(has_resources=True, valid_dates=False, enough_context=True)
        == "invalid_dates"
    )
    assert (
        route.evaluate(has_resources=True, valid_dates=True, enough_context=False)
        == "insufficient_evidence"
    )
    assert (
        route.evaluate(has_resources=True, valid_dates=True, enough_context=True)
        == "propose"
    )


def test_gemini_provider_rejects_empty_invalid_and_transient_results(monkeypatch):
    monkeypatch.setattr(
        "app.academic_intelligence.gemini_provider.time.sleep", lambda _: None
    )
    for answer in ("", "not json", "{}"):
        fake = SimpleNamespace(
            interactions=SimpleNamespace(
                create=lambda **_: SimpleNamespace(output_text=answer)
            )
        )
        with pytest.raises(DomainError) as exc:
            GeminiProvider(None, client=fake).plan("{}")
        assert exc.value.code == "STUDY_PLAN_GENERATION_UNAVAILABLE"
    calls = []

    def throttled(**kwargs):
        calls.append(kwargs)
        raise errors.APIError(429, {"error": "rate limit"})

    fake = SimpleNamespace(interactions=SimpleNamespace(create=throttled))
    with pytest.raises(DomainError) as exc:
        GeminiProvider(None, client=fake).behavior("{}")
    assert exc.value.code == "GEMINI_RATE_LIMIT"
    assert len(calls) == 2

    for code in (500, 503):
        attempts = []

        def unavailable(**kwargs):
            attempts.append(kwargs)
            raise errors.APIError(code, {"error": "unavailable"})

        fake = SimpleNamespace(interactions=SimpleNamespace(create=unavailable))
        with pytest.raises(DomainError) as exc:
            GeminiProvider(None, client=fake).behavior("{}")
        assert exc.value.code == "STUDY_PLAN_GENERATION_UNAVAILABLE"
        assert len(attempts) == 2


def test_gemini_provider_uses_structured_output_and_handles_timeout():
    payload = PlanProposal(
        name="Plan propuesto",
        objective="Practicar la materia existente.",
        start_date=datetime(2030, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2030, 1, 7, tzinfo=timezone.utc),
        explanation="Hay actividad pendiente.",
        subject_ids=[1],
        activity_ids=[],
        session_ids=[],
        proposed_challenges=[],
        reasoning_summary="Una materia activa.",
    )
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(payload.model_dump(mode="json")))

    provider = GeminiProvider(
        None, client=SimpleNamespace(interactions=SimpleNamespace(create=create))
    )
    assert provider.plan("{}") == payload
    assert calls[0]["model"] == "gemini-3.8-flash"
    assert calls[0]["input"] == "{}"
    assert "untrusted" in calls[0]["system_instruction"]
    assert calls[0]["response_format"]["mime_type"] == "application/json"
    assert "schema" in calls[0]["response_format"]

    def timeout(**kwargs):
        raise TimeoutError()

    provider = GeminiProvider(
        None, client=SimpleNamespace(interactions=SimpleNamespace(create=timeout))
    )
    with pytest.raises(DomainError) as exc:
        provider.plan("{}")
    assert exc.value.code == "STUDY_PLAN_GENERATION_UNAVAILABLE"


def test_proposal_validation_rejects_foreign_id_and_duplicate_id():
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    proposal = PlanProposal(
        name="Plan",
        objective="Practicar.",
        start_date=now,
        end_date=now + timedelta(days=7),
        explanation="Hay materia.",
        subject_ids=[999],
        activity_ids=[],
        session_ids=[],
        proposed_challenges=[],
        reasoning_summary="Materia registrada.",
    )
    context = SimpleNamespace(
        subject_ids={1},
        activity_ids=set(),
        session_ids=set(),
        subjects=[SimpleNamespace(id=1)],
        activities=[],
        sessions=[],
    )
    with pytest.raises(DomainError):
        validate_proposal(proposal, context)
    with pytest.raises(DomainError):
        validate_proposal(proposal.model_copy(update={"subject_ids": [1, 1]}), context)


def test_behavior_rejects_diagnosis_and_unowned_evidence(monkeypatch):
    context = SimpleNamespace(
        finished_count=5,
        subject_ids={1},
        activity_ids=set(),
        session_ids=set(),
        evidence_catalog={"subject:1": "Materia propia registrada."},
        as_json=lambda: "{}",
    )
    monkeypatch.setattr(
        "app.services.behavior_analysis_service.AcademicContext",
        lambda db, user_id: context,
    )
    db = SimpleNamespace(rollback=lambda: None)

    def analyze(observation, evidence):
        provider = SimpleNamespace(
            behavior=lambda _: BehaviorProposal(
                observations=[
                    BehaviorObservation(
                        observation=observation,
                        evidence=evidence,
                        question="¿Cómo interpretas esto?",
                        confidence_basis="Cinco sesiones; muestra limitada.",
                        related_subject_ids=[1],
                        related_activity_ids=[],
                        related_session_ids=[],
                    )
                ]
            )
        )
        return BehaviorAnalysisService(db, provider).analyze(1)

    with pytest.raises(DomainError):
        analyze("Tienes un trastorno.", ["subject:1"])
    with pytest.raises(DomainError):
        analyze("Podría haber una diferencia.", ["subject:999"])
    good = analyze("Podría haber una diferencia.", ["subject:1"])
    assert good.observations[0].evidence == ["Materia propia registrada."]


def test_contextual_challenge_requires_matching_target_and_owned_evidence():
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    context = SimpleNamespace(
        subject_ids={1},
        activity_ids={2},
        session_ids=set(),
        subjects=[SimpleNamespace(id=1)],
        activities=[SimpleNamespace(id=2, subject_id=1)],
        sessions=[],
        evidence_catalog={
            "subject:1": "Materia propia.",
            "activity:2": "Actividad propia.",
        },
    )
    base = ProposedChallenge(
        title="Cerrar actividad",
        objective="Completar lo pendiente.",
        explanation="Actividad registrada.",
        evidence=["activity:2"],
        target_type="activity_completion",
        target_id=2,
        subject_id=1,
        activity_id=2,
        target_value={"status": "completed"},
        measurable_condition="Actividad completada.",
    )
    plan = PlanProposal(
        name="Plan",
        objective="Practicar.",
        start_date=start,
        end_date=start + timedelta(days=7),
        explanation="Actividad pendiente.",
        subject_ids=[1],
        activity_ids=[2],
        session_ids=[],
        proposed_challenges=[base],
        reasoning_summary="Actividad existente.",
    )
    _, challenges = validate_proposal(plan, context)
    assert challenges[0].generation_criteria["evidence"] == ["Actividad propia."]
    for bad in (
        base.model_copy(update={"target_id": 1}),
        base.model_copy(update={"evidence": ["activity:999"]}),
    ):
        with pytest.raises(DomainError):
            validate_proposal(
                plan.model_copy(update={"proposed_challenges": [bad]}), context
            )
