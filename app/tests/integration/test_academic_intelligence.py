from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.academic_intelligence.gemini_provider import GeminiProvider
from app.academic_intelligence.gemini_schemas import (
    BehaviorObservation,
    BehaviorProposal,
    PlanProposal,
    ProposedChallenge,
)
from app.models.study_plans import StudyPlan, StudyPlanDecision
from app.models.user import User
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
    old = client.get(f"{BASE}/{plan['id']}/challenges", headers=headers).json()["items"]
    assert len(old) == 1 and old[0]["source"] == "ai"
    assert old[0]["generation_criteria"]["evidence"]

    invalid = first.model_copy(update={"activity_ids": [99999999]})
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: invalid)
    failed = client.post(f"{BASE}/{plan['id']}/regenerate", headers=headers)
    assert failed.status_code == 503
    assert client.get(f"{BASE}/{plan['id']}", headers=headers).json()["decisions"] == []
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
    assert decision["chosen_value"] is None
    challenges = client.get(f"{BASE}/{plan['id']}/challenges", headers=headers).json()[
        "items"
    ]
    assert [row["status"] for row in challenges] == ["cancelled", "pending"]
    again = client.post(f"{BASE}/{plan['id']}/regenerate", headers=headers)
    assert again.status_code == 200, again.text
    assert [
        row["status"]
        for row in client.get(
            f"{BASE}/{plan['id']}/challenges", headers=headers
        ).json()["items"]
    ] == ["cancelled", "cancelled", "pending"]
    accepted = client.post(f"{BASE}/{plan['id']}/accept", headers=headers)
    assert accepted.status_code == 200 and accepted.json()["status"] == "active"

    other_registration = {**registration, "email": "other-ai@example.com"}
    _, other_headers, _, _ = setup_activity(client, other_registration)
    monkeypatch.setattr(GeminiProvider, "plan", lambda self, context: first)
    foreign = client.post(BASE + "/generate", headers=other_headers)
    assert foreign.status_code == 503
    assert client.get(BASE, headers=other_headers).json()["items"] == []
    isolated = client.post("/api/v1/analysis/behavior", headers=other_headers)
    assert isolated.status_code == 200
    assert isolated.json()["finished_session_count"] == 0


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
