from datetime import datetime, timezone

from sqlalchemy import select

from app.models.study_plans import StudyPlan
from app.models.user import User
from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_study_sessions import create_plan as create_session
from app.tests.integration.test_subjects import create as create_subject
from app.tests.integration.test_subjects import onboard

BASE = "/api/v1/study-plans"


def plan_body(subject_ids=None, activity_ids=None, study_session_ids=None, **overrides):
    value = {
        "name": "Semana de cálculo",
        "objective": "Preparar el parcial con práctica distribuida.",
        "start_at": "2030-01-01T00:00:00Z",
        "end_at": "2030-01-10T00:00:00Z",
        "subject_ids": subject_ids or [],
        "activity_ids": activity_ids or [],
        "study_session_ids": study_session_ids or [],
    }
    value.update(overrides)
    return value


def create_study_plan(client, headers, **values):
    response = client.post(BASE, headers=headers, json=plan_body(**values))
    assert response.status_code == 201, response.text
    return response.json()


def test_plan_crud_relations_decision_history_undo_and_state_transitions(
    client, registration
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    session = create_session(
        client,
        headers,
        activity_data["subject_id"],
        activity["id"],
        planned_start_at="2030-01-02T12:00:00Z",
        planned_duration=45,
    )
    plan = create_study_plan(
        client,
        headers,
        subject_ids=[activity_data["subject_id"]],
        activity_ids=[activity["id"]],
        study_session_ids=[session["id"]],
    )
    path = f"{BASE}/{plan['id']}"

    assert plan["source"] == "manual" and plan["status"] == "draft"
    assert "user_id" not in plan
    assert [row["id"] for row in plan["activities"]] == [activity["id"]]
    assert [row["id"] for row in plan["study_sessions"]] == [session["id"]]
    assert plan["priority_order"] == [activity["id"]]
    assert plan["activity_dependency_order"] == [activity["id"]]
    assert sum(day["planned_minutes"] for day in plan["weekly_rhythm"]) == 45
    assert plan["schedule_conflict"] is False
    assert plan["candidate_slots"]
    assert plan["hierarchy"]["children"][0]["kind"] == "subject"
    assert client.get(path, headers=headers).json() == plan
    assert client.get(path, headers=headers).headers["cache-control"] == "no-store"

    changed = client.put(
        path,
        headers=headers,
        json=plan_body(
            subject_ids=[activity_data["subject_id"]],
            activity_ids=[activity["id"]],
            study_session_ids=[session["id"]],
            name="Semana de repaso",
            objective="Preparar el parcial con recuperación activa.",
        ),
    )
    assert changed.status_code == 200, changed.text
    assert [entry["field_path"] for entry in changed.json()["decisions"]] == [
        "name",
        "objective",
    ]
    assert all(entry["action"] == "edited" for entry in changed.json()["decisions"])

    first_undo = client.post(path + "/undo", headers=headers)
    assert first_undo.status_code == 200, first_undo.text
    assert first_undo.json()["name"] == "Semana de repaso"
    assert (
        first_undo.json()["objective"]
        == "Preparar el parcial con práctica distribuida."
    )
    second_undo = client.post(path + "/undo", headers=headers)
    assert second_undo.status_code == 200
    assert second_undo.json()["name"] == "Semana de cálculo"
    assert len(second_undo.json()["decisions"]) == 4

    activated = client.post(path + "/activate", headers=headers)
    assert activated.status_code == 200 and activated.json()["status"] == "active"
    completed = client.post(path + "/complete", headers=headers)
    assert completed.status_code == 200 and completed.json()["status"] == "completed"
    conflict = client.post(path + "/abandon", headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "STUDY_PLAN_STATE_CONFLICT"


def test_plan_keeps_overlapping_sessions_visible_as_schedule_conflict(
    client, registration
):
    _, headers, activity_data, activity = setup_activity(client, registration)
    first = create_session(
        client,
        headers,
        activity_data["subject_id"],
        activity["id"],
        planned_start_at="2030-01-02T12:00:00Z",
        planned_duration=45,
    )
    second = create_session(
        client,
        headers,
        activity_data["subject_id"],
        activity["id"],
        planned_start_at="2030-01-02T12:00:00Z",
        planned_duration=30,
    )

    outside_plan = client.post(
        BASE,
        headers=headers,
        json=plan_body(
            subject_ids=[activity_data["subject_id"]],
            activity_ids=[activity["id"]],
            study_session_ids=[first["id"]],
            end_at="2030-01-02T12:30:00Z",
        ),
    )
    assert outside_plan.status_code == 409

    overlapping = create_study_plan(
        client,
        headers,
        subject_ids=[activity_data["subject_id"]],
        activity_ids=[activity["id"]],
        study_session_ids=[first["id"], second["id"]],
    )
    assert [row["id"] for row in overlapping["study_sessions"]] == [
        first["id"],
        second["id"],
    ]
    assert overlapping["schedule_conflict"] is True
    assert overlapping["candidate_slots"] == []


def test_plan_list_pagination_safe_delete_and_manual_abandon(client, registration):
    _, headers = onboard(client, registration)
    first = create_study_plan(client, headers)
    second = create_study_plan(client, headers, name="Plan sin relaciones")

    page = client.get(BASE, headers=headers, params={"limit": 1})
    assert page.status_code == 200
    assert [item["id"] for item in page.json()["items"]] == [first["id"]]
    assert page.json()["next_after_id"] == first["id"]
    next_page = client.get(
        BASE,
        headers=headers,
        params={"limit": 1, "after_id": page.json()["next_after_id"]},
    )
    assert [item["id"] for item in next_page.json()["items"]] == [second["id"]]
    assert next_page.json()["next_after_id"] is None

    empty_plan = create_study_plan(client, headers, name="Borrador sin vínculos")
    delete = client.delete(f"{BASE}/{empty_plan['id']}?confirm=true", headers=headers)
    assert delete.status_code == 204
    assert client.get(f"{BASE}/{empty_plan['id']}", headers=headers).status_code == 404
    assert (
        client.delete(f"{BASE}/{first['id']}?confirm=true", headers=headers).status_code
        == 409
    )

    abandoned = client.post(f"{BASE}/{second['id']}/abandon", headers=headers)
    assert abandoned.status_code == 200
    assert abandoned.json()["status"] == "abandoned"


def test_plan_ownership_and_resource_context_are_strict(client, registration):
    _, headers, activity_data, activity = setup_activity(client, registration)
    _, other_headers, other_payload, other_activity = setup_activity(
        client, {**registration, "email": "other-study-plan@example.com"}
    )
    own_second_subject = create_subject(client, headers, name="Física").json()
    own_second_activity = client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            "title": "Guía de física",
            "subject_id": own_second_subject["id"],
            "deadline": "2030-01-04T12:00:00Z",
            "priority": "medium",
            "status": "pending",
            "estimated_duration": 45,
            "notes": None,
        },
    )
    assert own_second_activity.status_code == 201
    own_plan = create_study_plan(
        client, headers, subject_ids=[activity_data["subject_id"]]
    )
    own_path = f"{BASE}/{own_plan['id']}"

    assert client.get(own_path, headers=other_headers).status_code == 404
    assert (
        client.put(own_path, headers=other_headers, json=plan_body()).status_code == 404
    )
    assert (
        client.delete(own_path + "?confirm=true", headers=other_headers).status_code
        == 404
    )

    foreign_activity = client.post(
        BASE,
        headers=headers,
        json=plan_body(
            subject_ids=[activity_data["subject_id"]],
            activity_ids=[other_activity["id"]],
        ),
    )
    assert foreign_activity.status_code == 409
    wrong_subject = client.post(
        BASE,
        headers=headers,
        json=plan_body(
            subject_ids=[activity_data["subject_id"]],
            activity_ids=[own_second_activity.json()["id"]],
        ),
    )
    assert wrong_subject.status_code == 409
    assert wrong_subject.json()["error"]["code"] == "STUDY_PLAN_RESOURCE_CONFLICT"

    duplicate = client.post(
        BASE,
        headers=headers,
        json=plan_body(
            subject_ids=[activity_data["subject_id"], activity_data["subject_id"]]
        ),
    )
    assert duplicate.status_code == 422
    assert other_payload["subject_id"] != activity_data["subject_id"]


def test_ai_decisions_are_explicit_and_generation_is_not_faked(
    client, registration, database
):
    _, headers = onboard(client, registration)
    start_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2030, 1, 8, tzinfo=timezone.utc)
    with database.session() as db:
        owner_id = db.scalar(select(User.id).where(User.email == registration["email"]))
        proposed = StudyPlan(
            user_id=owner_id,
            name="Propuesta de física",
            objective="Repasar cinemática",
            start_at=start_at,
            end_at=end_at,
            status="draft",
            source="ai",
        )
        db.add(proposed)
        db.commit()
        accepted_id = proposed.id
        rejected = StudyPlan(
            user_id=owner_id,
            name="Propuesta alternativa",
            objective="Resolver problemas",
            start_at=start_at,
            end_at=end_at,
            status="draft",
            source="ai",
        )
        db.add(rejected)
        db.commit()
        rejected_id = rejected.id
        regen = StudyPlan(
            user_id=owner_id,
            name="Propuesta a regenerar",
            objective="Estudiar con práctica",
            start_at=start_at,
            end_at=end_at,
            status="draft",
            source="ai",
        )
        db.add(regen)
        db.commit()
        regen_id = regen.id

    accepted = client.post(f"{BASE}/{accepted_id}/accept", headers=headers)
    assert accepted.status_code == 200 and accepted.json()["status"] == "active"
    accepted_decision = accepted.json()["decisions"][-1]
    assert accepted_decision["action"] == "accepted"
    assert accepted_decision["proposed_value"] == accepted_decision["chosen_value"]
    rejected_response = client.post(f"{BASE}/{rejected_id}/reject", headers=headers)
    assert rejected_response.status_code == 200
    assert rejected_response.json()["status"] == "abandoned"
    rejected_decision = rejected_response.json()["decisions"][-1]
    assert rejected_decision["action"] == "rejected"
    assert rejected_decision["proposed_value"] is not None
    assert rejected_decision["chosen_value"] is None

    unavailable = client.post(f"{BASE}/{regen_id}/regenerate", headers=headers)
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "STUDY_PLAN_GENERATION_UNAVAILABLE"
