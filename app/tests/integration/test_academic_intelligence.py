from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.academic_intelligence.ai_plan_snapshot import AiPlanProposalSnapshot
from app.academic_intelligence.gemini_provider import GeminiProvider
from app.academic_intelligence.gemini_schemas import (
    BehaviorObservation,
    BehaviorProposal,
    PlanProposal,
    ProposedChallenge,
)
from app.core.domain_error import DomainError
from app.models.study_plans import StudyPlan, StudyPlanDecision
from app.models.user import User
from app.services.study_plan_service import StudyPlanService
from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_study_sessions import create_plan as create_session

BASE = "/api/v1/study-plans"


def proposal(subject_id, activity_id, *, name="Propuesta contextual"):
    return PlanProposal(
        name=name,
        objective="Preparar la actividad pendiente en una semana.",
        start_date=datetime(2030, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2030, 1, 10, tzinfo=timezone.utc),
        explanation="La actividad tiene una fecha límite cercana.",
        subject_ids=[subject_id],
        activity_ids=[activity_id],
        session_ids=[],
        proposed_challenges=[
            ProposedChallenge(
                title="Cerrar la actividad pendiente",
                objective="Completa la actividad vinculada al plan.",
                explanation="La actividad registrada aún está pendiente.",
                evidence=[f"activity:{activity_id}"],
                target_type="activity_completion",
                target_id=activity_id,
                subject_id=subject_id,
                activity_id=activity_id,
                target_value={"status": "completed"},
                measurable_condition="La actividad cambia a completada.",
            )
        ],
        reasoning_summary="Se relacionó la fecha límite con la actividad existente.",
    )


def test_generate_and_regenerate_are_atomic(
    client, registration, database, monkeypatch
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    assert client.post(BASE + "/generate").status_code == 401
    assert client.post(BASE + "/generate", headers=headers).status_code == 503
    first = proposal(activity_data["subject_id"], activity["id"])
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    generated = client.post(BASE + "/generate", headers=headers)
    assert generated.status_code == 201, generated.text
    assert generated.headers["cache-control"] == "no-store"
    plan = generated.json()["plan"]
    assert plan["source"] == "ai" and plan["status"] == "draft"
    assert generated.json()["explanation"] == first.explanation
    initial_snapshot = plan["ai_proposal_snapshot"]
    assert initial_snapshot["schema_version"] == 1
    assert initial_snapshot["model"] == "gemini-3.8-flash"
    assert initial_snapshot["explanation"] == first.explanation
    assert initial_snapshot["reasoning_summary"] == first.reasoning_summary
    assert initial_snapshot["plan"]["name"] == first.name
    assert initial_snapshot["plan"]["activity_ids"] == [activity["id"]]
    assert initial_snapshot["proposed_challenges"][0]["title"] == (
        first.proposed_challenges[0].title
    )
    refreshed = client.get(f"{BASE}/{plan['id']}", headers=headers).json()
    assert refreshed["ai_proposal_snapshot"] == initial_snapshot
    assert refreshed["explanation"] == first.explanation
    assert refreshed["reasoning_summary"] == first.reasoning_summary
    old = client.get(f"{BASE}/{plan['id']}/challenges", headers=headers).json()["items"]
    assert len(old) == 1 and old[0]["source"] == "ai"
    assert old[0]["generation_criteria"]["evidence"]

    invalid = first.model_copy(update={"activity_ids": [99999999]})
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: invalid)
    failed = client.post(f"{BASE}/{plan['id']}/regenerate", headers=headers)
    assert failed.status_code == 503
    after_failure = client.get(f"{BASE}/{plan['id']}", headers=headers).json()
    assert after_failure["decisions"] == []
    assert after_failure["ai_proposal_snapshot"] == initial_snapshot
    with database.session() as db:
        owner_id = db.scalar(select(User.id).where(User.email == registration["email"]))
        assert (
            db.scalar(
                select(func.count())
                .select_from(StudyPlan)
                .where(StudyPlan.user_id == owner_id)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(StudyPlanDecision)
                .where(StudyPlanDecision.user_id == owner_id)
            )
            == 0
        )

    second = proposal(
        activity_data["subject_id"], activity["id"], name="Propuesta revisada"
    )
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: second)
    updated = client.post(f"{BASE}/{plan['id']}/regenerate", headers=headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Propuesta revisada"
    decision = updated.json()["decisions"][-1]
    assert decision["action"] == "regenerated"
    assert decision["proposed_value"]["plan"]["name"] == "Propuesta contextual"
    assert decision["proposed_value"] == initial_snapshot
    assert decision["chosen_value"] is None
    second_snapshot = updated.json()["ai_proposal_snapshot"]
    assert second_snapshot["plan"]["name"] == "Propuesta revisada"
    assert second_snapshot["explanation"] == second.explanation
    assert (
        client.get(f"{BASE}/{plan['id']}", headers=headers).json()[
            "ai_proposal_snapshot"
        ]
        == second_snapshot
    )
    challenges = client.get(f"{BASE}/{plan['id']}/challenges", headers=headers).json()[
        "items"
    ]
    assert [row["status"] for row in challenges] == ["cancelled", "pending"]
    again = client.post(f"{BASE}/{plan['id']}/regenerate", headers=headers)
    assert again.status_code == 200, again.text
    assert again.json()["decisions"][-1]["proposed_value"] == second_snapshot
    assert [
        row["status"]
        for row in client.get(
            f"{BASE}/{plan['id']}/challenges", headers=headers
        ).json()["items"]
    ] == ["cancelled", "cancelled", "pending"]
    accepted = client.post(f"{BASE}/{plan['id']}/accept", headers=headers)
    assert accepted.status_code == 200 and accepted.json()["status"] == "active"
    assert (
        accepted.json()["ai_proposal_snapshot"] == again.json()["ai_proposal_snapshot"]
    )
    assert (
        accepted.json()["decisions"][-1]["proposed_value"]
        == again.json()["ai_proposal_snapshot"]
    )

    other_registration = {**registration, "email": "other-ai@example.com"}
    _, other_headers, _, _ = setup_activity(client, other_registration)
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    foreign = client.post(BASE + "/generate", headers=other_headers)
    assert foreign.status_code == 503
    assert client.get(BASE, headers=other_headers).json()["items"] == []
    isolated = client.post("/api/v1/analysis/behavior", headers=other_headers)
    assert isolated.status_code == 200
    assert isolated.json()["finished_session_count"] == 0


def test_manual_edit_reject_and_legacy_ai_snapshot_are_safe(
    client, registration, database, monkeypatch
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    body = {
        "name": "Plan manual",
        "objective": "Preparar la actividad",
        "start_at": "2030-01-01T00:00:00Z",
        "end_at": "2030-01-10T00:00:00Z",
        "subject_ids": [activity_data["subject_id"]],
        "activity_ids": [activity["id"]],
        "study_session_ids": [],
    }
    manual = client.post(BASE, headers=headers, json=body)
    assert manual.status_code == 201, manual.text
    assert manual.json()["ai_proposal_snapshot"] is None
    assert manual.json()["explanation"] is None
    assert (
        client.get(f"{BASE}/{manual.json()['id']}", headers=headers).json()[
            "ai_proposal_snapshot"
        ]
        is None
    )

    first = proposal(activity_data["subject_id"], activity["id"])
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    generated = client.post(BASE + "/generate", headers=headers)
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()["plan"]["id"]
    original = generated.json()["plan"]["ai_proposal_snapshot"]
    edited = client.put(
        f"{BASE}/{plan_id}",
        headers=headers,
        json={**body, "name": "Elección del usuario"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["ai_proposal_snapshot"] == original
    assert edited.json()["name"] == "Elección del usuario"
    rejected = client.post(f"{BASE}/{plan_id}/reject", headers=headers)
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["ai_proposal_snapshot"] == original
    assert rejected.json()["decisions"][-1]["action"] == "rejected"
    assert rejected.json()["decisions"][-1]["proposed_value"] == original
    assert (
        client.get(f"{BASE}/{plan_id}", headers=headers).json()["explanation"]
        == first.explanation
    )

    with database.session() as db:
        legacy = db.get(StudyPlan, plan_id)
        assert legacy is not None
        legacy.ai_proposal_snapshot = None
        db.commit()
    legacy_detail = client.get(f"{BASE}/{plan_id}", headers=headers)
    assert legacy_detail.status_code == 200
    assert legacy_detail.json()["ai_proposal_snapshot"] is None
    assert legacy_detail.json()["explanation"] is None

    accepted_plan = client.post(BASE + "/generate", headers=headers)
    assert accepted_plan.status_code == 201, accepted_plan.text
    accepted_id = accepted_plan.json()["plan"]["id"]
    accepted_original = accepted_plan.json()["plan"]["ai_proposal_snapshot"]
    assert (
        client.put(
            f"{BASE}/{accepted_id}",
            headers=headers,
            json={**body, "name": "Decisión final"},
        ).status_code
        == 200
    )
    acceptance = client.post(f"{BASE}/{accepted_id}/accept", headers=headers)
    assert acceptance.status_code == 200, acceptance.text
    accepted_decision = acceptance.json()["decisions"][-1]
    assert accepted_decision["proposed_value"] == accepted_original
    assert accepted_decision["chosen_value"]["name"] == "Decisión final"
    assert acceptance.json()["ai_proposal_snapshot"] == accepted_original


def test_ai_snapshot_size_checks_exact_postgresql_jsonb_bytes(database):
    with database.session() as db:
        service = StudyPlanService(db)
        # PostgreSQL JSONB renders {"x": "..."} with nine bytes of framing.
        service._validate_jsonb_size({"x": "a" * (32768 - 9)}, 32768)
        with pytest.raises(DomainError) as too_large:
            service._validate_jsonb_size({"x": "a" * (32769 - 9)}, 32768)
        assert too_large.value.code == "STUDY_PLAN_GENERATION_UNAVAILABLE"
        service._validate_jsonb_size({"x": "a" * (65536 - 9)}, 65536)
        with pytest.raises(DomainError) as decision_too_large:
            service._validate_jsonb_size({"x": "a" * (65537 - 9)}, 65536)
        assert decision_too_large.value.code == "STUDY_PLAN_GENERATION_UNAVAILABLE"


def test_oversized_ai_snapshot_creates_no_plan_or_challenge(
    client, registration, database, monkeypatch
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    first = proposal(activity_data["subject_id"], activity["id"])
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)

    class OversizedSnapshot:
        def as_storage(self):
            return {"explanation": "x" * 32769}

    monkeypatch.setattr(
        AiPlanProposalSnapshot,
        "from_proposal",
        classmethod(lambda cls, *args, **kwargs: OversizedSnapshot()),
    )
    rejected = client.post(BASE + "/generate", headers=headers)
    assert rejected.status_code == 503
    assert client.get(BASE, headers=headers).json()["items"] == []
    with database.session() as db:
        assert db.scalar(select(func.count()).select_from(StudyPlan)) == 0
        assert db.scalar(select(func.count()).select_from(StudyPlanDecision)) == 0


def test_oversized_regeneration_keeps_prior_snapshot_and_challenges(
    client, registration, monkeypatch
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    first = proposal(activity_data["subject_id"], activity["id"])
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    generated = client.post(BASE + "/generate", headers=headers)
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()["plan"]["id"]
    before = client.get(f"{BASE}/{plan_id}", headers=headers).json()
    previous_challenges = client.get(
        f"{BASE}/{plan_id}/challenges", headers=headers
    ).json()

    class OversizedSnapshot:
        def as_storage(self):
            return {"explanation": "x" * 32769}

    monkeypatch.setattr(
        AiPlanProposalSnapshot,
        "from_proposal",
        classmethod(lambda cls, *args, **kwargs: OversizedSnapshot()),
    )
    rejected = client.post(f"{BASE}/{plan_id}/regenerate", headers=headers)
    assert rejected.status_code == 503
    assert client.get(f"{BASE}/{plan_id}", headers=headers).json() == before
    assert client.get(f"{BASE}/{plan_id}/challenges", headers=headers).json() == (
        previous_challenges
    )


def test_regeneration_rejects_oversized_decision_before_mutating(
    client, registration, monkeypatch
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    first = proposal(activity_data["subject_id"], activity["id"])
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    generated = client.post(BASE + "/generate", headers=headers)
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()["plan"]["id"]
    before = client.get(f"{BASE}/{plan_id}", headers=headers).json()
    previous_challenges = client.get(
        f"{BASE}/{plan_id}/challenges", headers=headers
    ).json()
    original_check = StudyPlanService._validate_jsonb_size

    def reject_decision(self, value, limit):
        if limit == 65536:
            raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE")
        return original_check(self, value, limit)

    monkeypatch.setattr(StudyPlanService, "_validate_jsonb_size", reject_decision)
    rejected = client.post(f"{BASE}/{plan_id}/regenerate", headers=headers)
    assert rejected.status_code == 503
    assert client.get(f"{BASE}/{plan_id}", headers=headers).json() == before
    assert client.get(f"{BASE}/{plan_id}/challenges", headers=headers).json() == (
        previous_challenges
    )


def test_legacy_ai_plan_without_snapshot_regenerates_safely(
    client, registration, database, monkeypatch
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    first = proposal(activity_data["subject_id"], activity["id"])
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    generated = client.post(BASE + "/generate", headers=headers)
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()["plan"]["id"]
    with database.session() as db:
        legacy = db.get(StudyPlan, plan_id)
        assert legacy is not None
        legacy.ai_proposal_snapshot = None
        db.commit()
    assert (
        client.get(f"{BASE}/{plan_id}", headers=headers).json()["ai_proposal_snapshot"]
        is None
    )
    second = proposal(activity_data["subject_id"], activity["id"], name="Nuevo plan")
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: second)
    refreshed = client.post(f"{BASE}/{plan_id}/regenerate", headers=headers)
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["ai_proposal_snapshot"]["plan"]["name"] == "Nuevo plan"
    assert (
        refreshed.json()["decisions"][-1]["proposed_value"]["plan"]["name"]
        == first.name
    )


def test_behavior_threshold_zero_through_six(client, registration, monkeypatch):
    _, headers, activity_data, _ = setup_activity(client, registration)
    zero = client.post("/api/v1/analysis/behavior", headers=headers)
    assert zero.status_code == 200 and zero.json()["observations"] == []
    assert zero.json()["pattern_eligible"] is False
    clock = {"now": datetime(2030, 1, 2, 12, tzinfo=timezone.utc)}
    monkeypatch.setattr(
        "app.services.study_session_service.utc_now", lambda: clock["now"]
    )
    monkeypatch.setattr(
        GeminiProvider,
        "behavior",
        lambda self, context: BehaviorProposal(
            observations=[
                BehaviorObservation(
                    observation="Podría haber una diferencia entre plan y duración.",
                    evidence=[f"subject:{activity_data['subject_id']}"],
                    question="¿Cómo interpretas esa diferencia?",
                    confidence_basis="Solo cinco sesiones; la muestra es limitada.",
                    related_subject_ids=[activity_data["subject_id"]],
                    related_activity_ids=[],
                    related_session_ids=[],
                )
            ]
        ),
    )
    for count in range(1, 7):
        clock["now"] = datetime(2030, 1, count + 1, 12, tzinfo=timezone.utc)
        session = create_session(
            client,
            headers,
            activity_data["subject_id"],
            planned_start_at=clock["now"].isoformat(),
        )
        path = f"/api/v1/sessions/{session['id']}"
        assert client.post(path + "/start", headers=headers).status_code == 200
        clock["now"] += timedelta(minutes=30)
        finished = client.post(
            path + "/finish", headers=headers, json={"status": "completed"}
        )
        assert finished.status_code == 200, finished.text
        response = client.post("/api/v1/analysis/behavior", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["finished_session_count"] == count
        if count < 5:
            assert response.json()["pattern_eligible"] is False
            assert "patrón" not in response.json()["observations"][0]["observation"]
        else:
            assert response.json()["pattern_eligible"] is True
            assert response.json()["observations"][0]["question"].endswith("?")
