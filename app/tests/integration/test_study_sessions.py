from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import text

from app.core.domain_error import DomainError
from app.services.study_session_service import StudySessionService
from app.tests.database_tooling import database_checkout, migrate_test_schema
from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_subjects import create as create_subject
from app.tests.integration.test_subjects import onboard

BASE = "/api/v1/sessions"


def plan_body(subject_id, activity_id=None, **overrides):
    body = {
        "subject_id": subject_id,
        "activity_id": activity_id,
        "planned_start_at": "2030-01-02T12:00:00Z",
        "planned_duration": 30,
    }
    body.update(overrides)
    return body


def create_plan(client, headers, subject_id, activity_id=None, **overrides):
    response = client.post(
        BASE,
        headers=headers,
        json=plan_body(subject_id, activity_id, **overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def new_subject(client, registration, name="Matemáticas"):
    _, headers = onboard(client, registration)
    subject = create_subject(client, headers, name=name)
    assert subject.status_code == 201
    return headers, subject.json()


def test_planned_crud_pagination_and_safe_delete(client, registration):
    headers, first_subject = new_subject(client, registration)
    second = create_subject(client, headers, name="Física").json()
    original = create_plan(client, headers, first_subject["id"])
    assert original["execution_state"] == "planned"
    assert original["status"] is None
    assert original["start_at"] is None and original["end_at"] is None
    assert original["activity_id"] is None
    assert original["actual_duration"] == 0
    assert "user_id" not in original
    assert original["intervals"] == []
    assert original["created_at"] <= original["updated_at"]
    assert original["planned_duration"] == 30
    path = BASE + "/" + str(original["id"])
    assert client.get(path, headers=headers).json() == original

    updated = client.put(
        path,
        headers=headers,
        json=plan_body(
            second["id"],
            planned_start_at="2030-02-01T08:30:00-05:00",
            planned_duration=45,
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["subject_id"] == second["id"]
    assert updated.json()["activity_id"] is None
    assert updated.json()["planned_duration"] == 45
    assert updated.json()["created_at"] == original["created_at"]

    page = client.get(BASE, headers=headers, params={"limit": 1})
    assert page.status_code == 200 and len(page.json()["items"]) == 1
    assert "intervals" not in page.json()["items"][0]
    assert page.json()["next_cursor"] is None
    filtered = client.get(
        BASE,
        headers=headers,
        params={
            "subject_id": second["id"],
            "planned_start_from": "2030-02-01T13:30:00Z",
            "planned_start_to": "2030-03-01T00:00:00Z",
        },
    )
    assert [item["id"] for item in filtered.json()["items"]] == [original["id"]]

    assert client.delete(path, headers=headers).status_code == 422
    assert client.delete(path + "?confirm=false", headers=headers).status_code == 422
    deleted = client.delete(path + "?confirm=true", headers=headers)
    assert deleted.status_code == 204 and deleted.content == b""
    assert deleted.headers["cache-control"] == "no-store"
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path + "?confirm=true", headers=headers).status_code == 404


def test_activity_assignment_requires_same_owner_and_subject(client, registration):
    owner, headers, activity_body, activity = setup_activity(client, registration)
    own_subject = activity_body["subject_id"]
    another_subject = create_subject(client, headers, name="Física").json()["id"]
    valid = create_plan(client, headers, own_subject, activity["id"])
    assert valid["activity_id"] == activity["id"]

    mismatch = client.post(
        BASE,
        headers=headers,
        json=plan_body(another_subject, activity["id"]),
    )
    assert mismatch.status_code == 404
    assert mismatch.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"

    other = {**registration, "email": "other-session@example.com"}
    other_user, other_headers, other_body, other_activity = setup_activity(
        client, other
    )
    other_subject = other_body["subject_id"]
    foreign_subject = client.post(BASE, headers=headers, json=plan_body(other_subject))
    assert foreign_subject.status_code == 404
    assert foreign_subject.json()["error"]["code"] == "SUBJECT_NOT_FOUND"
    foreign_activity = client.post(
        BASE,
        headers=headers,
        json=plan_body(own_subject, other_activity["id"]),
    )
    assert foreign_activity.status_code == 404
    assert foreign_activity.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"

    path = BASE + "/" + str(valid["id"])
    foreign = client.get(path, headers=other_headers)
    missing = client.get(BASE + "/2147483647", headers=other_headers)
    assert foreign.status_code == 404 and foreign.json() == missing.json()
    assert client.get(BASE, headers=other_headers).json()["items"] == []
    assert owner["user"]["id"] != other_user["user"]["id"]


def test_timer_counts_only_closed_intervals_and_preserves_multiple_pauses(
    client, registration, database, monkeypatch
):
    headers, subject = new_subject(client, registration)
    clock = {"now": datetime(2030, 1, 1, tzinfo=timezone.utc)}
    monkeypatch.setattr(
        "app.services.study_session_service.utc_now", lambda: clock["now"]
    )
    created = create_plan(client, headers, subject["id"])
    path = BASE + "/" + str(created["id"])

    started = client.post(path + "/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["execution_state"] == "running"
    assert started.json()["start_at"] == clock["now"].isoformat().replace("+00:00", "Z")
    assert started.json()["intervals"][0]["ended_at"] is None
    assert started.json()["actual_duration"] == 0

    clock["now"] += timedelta(seconds=10)
    paused = client.post(path + "/pause", headers=headers)
    assert paused.status_code == 200
    assert paused.json()["execution_state"] == "paused"
    assert Decimal(str(paused.json()["actual_duration"])) == Decimal("10.000000")
    assert client.post(path + "/pause", headers=headers).status_code == 409

    clock["now"] += timedelta(seconds=5)
    resumed = client.post(path + "/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["execution_state"] == "running"
    assert len(resumed.json()["intervals"]) == 2
    assert resumed.json()["intervals"][1]["ended_at"] is None
    assert client.post(path + "/resume", headers=headers).status_code == 409

    clock["now"] += timedelta(seconds=7)
    second_pause = client.post(path + "/pause", headers=headers)
    assert Decimal(str(second_pause.json()["actual_duration"])) == Decimal("17.000000")

    clock["now"] += timedelta(seconds=8)
    second_resume = client.post(path + "/resume", headers=headers)
    assert second_resume.status_code == 200
    clock["now"] += timedelta(seconds=10)
    finished = client.post(
        path + "/finish",
        headers=headers,
        json={
            "status": "partial",
            "context": "other",
            "other_text": "Cambié de tarea",
        },
    )
    assert finished.status_code == 200
    result = finished.json()
    assert result["execution_state"] == "finished" and result["status"] == "partial"
    assert result["context"] == "other" and result["other_text"] == "Cambié de tarea"
    assert Decimal(str(result["actual_duration"])) == Decimal("27.000000")
    assert len(result["intervals"]) == 3
    interval_seconds = [
        (
            datetime.fromisoformat(interval["ended_at"].replace("Z", "+00:00"))
            - datetime.fromisoformat(interval["started_at"].replace("Z", "+00:00"))
        ).total_seconds()
        for interval in result["intervals"]
    ]
    assert interval_seconds == [10.0, 7.0, 10.0]
    assert all(interval["ended_at"] is not None for interval in result["intervals"])

    assert (
        client.post(
            path + "/finish", headers=headers, json={"status": "completed"}
        ).status_code
        == 409
    )

    with database.session() as db:
        persisted = db.execute(
            text(
                "SELECT actual_duration, execution_state "
                "FROM study_sessions WHERE id=:id"
            ),
            {"id": created["id"]},
        ).one()
        count, open_count = db.execute(
            text(
                "SELECT count(*), count(*) FILTER (WHERE ended_at IS NULL) "
                "FROM study_session_intervals WHERE session_id=:id"
            ),
            {"id": created["id"]},
        ).one()
    assert persisted.actual_duration == Decimal("27.000000")
    assert persisted.execution_state == "finished"
    assert count == 3 and open_count == 0


def test_unstarted_postpone_cancel_and_completed_precondition(client, registration):
    headers, subject = new_subject(client, registration)
    completed_plan = create_plan(client, headers, subject["id"])
    path = BASE + "/" + str(completed_plan["id"])
    invalid = client.post(
        path + "/finish", headers=headers, json={"status": "completed"}
    )
    assert invalid.status_code == 409
    assert client.get(path, headers=headers).json()["execution_state"] == "planned"
    postponed = client.post(
        path + "/finish", headers=headers, json={"status": "postponed"}
    )
    assert postponed.status_code == 200
    assert postponed.json()["status"] == "postponed"
    assert postponed.json()["start_at"] is None
    assert postponed.json()["end_at"] is None
    assert postponed.json()["actual_duration"] == 0
    assert postponed.json()["intervals"] == []
    assert (
        client.put(path, headers=headers, json=plan_body(subject["id"])).status_code
        == 409
    )
    assert client.delete(path + "?confirm=true", headers=headers).status_code == 409

    cancelled = create_plan(client, headers, subject["id"])
    result = client.post(
        BASE + "/" + str(cancelled["id"]) + "/finish",
        headers=headers,
        json={"status": "cancelled"},
    )
    assert result.status_code == 200 and result.json()["status"] == "cancelled"


def test_double_transitions_and_active_session_limit(client, registration, monkeypatch):
    headers, subject = new_subject(client, registration)
    clock = {"now": datetime(2030, 1, 1, tzinfo=timezone.utc)}
    monkeypatch.setattr(
        "app.services.study_session_service.utc_now", lambda: clock["now"]
    )
    first = create_plan(client, headers, subject["id"])
    second = create_plan(client, headers, subject["id"])
    path = BASE + "/" + str(first["id"])
    other_path = BASE + "/" + str(second["id"])

    assert client.post(path + "/pause", headers=headers).status_code == 409
    assert client.post(path + "/resume", headers=headers).status_code == 409
    assert client.post(path + "/start", headers=headers).status_code == 200
    assert client.post(path + "/start", headers=headers).status_code == 409
    conflict = client.post(other_path + "/start", headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "STUDY_SESSION_ACTIVE_CONFLICT"

    clock["now"] += timedelta(seconds=5)
    assert client.post(path + "/pause", headers=headers).status_code == 200
    assert client.post(path + "/pause", headers=headers).status_code == 409
    conflict = client.post(other_path + "/start", headers=headers)
    assert conflict.json()["error"]["code"] == "STUDY_SESSION_ACTIVE_CONFLICT"

    clock["now"] += timedelta(seconds=5)
    assert client.post(path + "/resume", headers=headers).status_code == 200
    assert client.post(path + "/resume", headers=headers).status_code == 409
    clock["now"] += timedelta(seconds=5)
    finished = client.post(
        path + "/finish", headers=headers, json={"status": "completed"}
    )
    assert finished.status_code == 200
    assert (
        client.post(
            path + "/finish", headers=headers, json={"status": "completed"}
        ).status_code
        == 409
    )


def test_delete_with_execution_history_is_blocked_and_dependencies_remain(
    client, registration, database, monkeypatch
):
    user, headers, activity_body, activity = setup_activity(client, registration)
    clock = {"now": datetime(2030, 1, 1, tzinfo=timezone.utc)}
    monkeypatch.setattr(
        "app.services.study_session_service.utc_now", lambda: clock["now"]
    )
    created = create_plan(client, headers, activity_body["subject_id"], activity["id"])
    path = BASE + "/" + str(created["id"])
    assert client.post(path + "/start", headers=headers).status_code == 200
    clock["now"] += timedelta(seconds=4)
    assert client.post(path + "/pause", headers=headers).status_code == 200
    blocked = client.delete(path + "?confirm=true", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "STUDY_SESSION_HISTORY_CONFLICT"
    assert client.get(path, headers=headers).status_code == 200

    blocked_activity = client.delete(
        f"/api/v1/activities/{activity['id']}?confirm=true", headers=headers
    )
    assert blocked_activity.status_code == 409
    blocked_subject = client.delete(
        f"/api/v1/subjects/{activity_body['subject_id']}?confirm=true",
        headers=headers,
    )
    assert blocked_subject.status_code == 409
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM study_sessions")) == 1
        assert db.scalar(text("SELECT count(*) FROM study_session_intervals")) == 1
        assert db.scalar(text("SELECT count(*) FROM activities")) == 1
        assert db.scalar(text("SELECT count(*) FROM subjects")) == 1
    assert user["user"]["id"] > 0


def test_filters_cursor_ownership_and_no_store(client, registration):
    owner, headers = onboard(client, registration)
    subject = create_subject(client, headers).json()
    created = [
        create_plan(
            client,
            headers,
            subject["id"],
            planned_start_at="2030-01-01T12:00:00Z",
        )
        for _ in range(3)
    ]
    postponed = client.post(
        BASE + "/" + str(created[1]["id"]) + "/finish",
        headers=headers,
        json={"status": "postponed"},
    )
    assert postponed.status_code == 200
    first = client.get(BASE, headers=headers, params={"limit": 2})
    assert first.status_code == 200 and len(first.json()["items"]) == 2
    cursor = first.json()["next_cursor"]
    assert cursor is not None
    second = client.get(
        BASE,
        headers=headers,
        params={
            "limit": 2,
            "after_planned_start_at": cursor["after_planned_start_at"],
            "after_id": cursor["after_id"],
        },
    )
    assert len(second.json()["items"]) == 1
    assert second.json()["next_cursor"] is None
    filtered = client.get(
        BASE,
        headers=headers,
        params={
            "subject_id": subject["id"],
            "execution_state": "finished",
            "status": "postponed",
        },
    )
    assert [item["id"] for item in filtered.json()["items"]] == [created[1]["id"]]
    invalid_cursor = client.get(BASE, headers=headers, params={"after_id": 1})
    assert invalid_cursor.status_code == 422
    assert invalid_cursor.headers["cache-control"] == "no-store"

    other_user, other_headers = onboard(
        client, {**registration, "email": "list-owner@example.com"}
    )
    other_subject = create_subject(client, other_headers, "Física").json()
    other_plan = create_plan(client, other_headers, other_subject["id"])
    own_list = client.get(BASE, headers=headers).json()["items"]
    assert {item["id"] for item in own_list} == {item["id"] for item in created}
    assert (
        client.get(
            BASE, headers=headers, params={"subject_id": other_subject["id"]}
        ).json()["items"]
        == []
    )
    assert own_list and all("user_id" not in item for item in own_list)

    foreign = client.get(BASE + "/" + str(other_plan["id"]), headers=headers)
    absent = client.get(BASE + "/2147483647", headers=headers)
    assert foreign.status_code == 404 and foreign.json() == absent.json()
    assert foreign.headers["cache-control"] == "no-store"
    assert owner["user"]["id"] != other_user["user"]["id"]


def test_auth_onboarding_csrf_and_no_store(client, registration):
    body = plan_body(1)
    unauthorized = client.get(BASE)
    assert unauthorized.status_code == 401
    assert unauthorized.headers["cache-control"] == "no-store"
    assert client.post(BASE, json=body).status_code == 401

    registered = client.post("/api/v1/auth/register", json=registration)
    assert registered.status_code == 201
    headers = {"Authorization": "Bearer " + registered.json()["access_token"]}
    incomplete = client.post(BASE, headers=headers, json=body)
    assert incomplete.status_code == 403
    assert incomplete.json()["error"]["code"] == "ONBOARDING_REQUIRED"
    assert incomplete.headers["cache-control"] == "no-store"
    assert client.post("/api/v1/auth/refresh").status_code == 403
    assert client.post("/api/v1/auth/logout").status_code == 403


def test_concurrent_start_allows_only_one_active_session(
    client, registration, database
):
    user, headers = onboard(client, registration)
    subject = create_subject(client, headers).json()
    first = create_plan(client, headers, subject["id"])
    second = create_plan(client, headers, subject["id"])
    barrier = Barrier(2)

    def start(session_id):
        with database.session() as db:
            barrier.wait(timeout=10)
            try:
                return StudySessionService(db).start(user["user"]["id"], session_id).id
            except DomainError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(start, [first["id"], second["id"]]))
    assert sum(isinstance(value, int) for value in outcomes) == 1
    assert outcomes.count("STUDY_SESSION_ACTIVE_CONFLICT") == 1
    with database.session() as db:
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM study_sessions "
                    "WHERE execution_state IN ('running','paused')"
                )
            )
            == 1
        )


def test_concurrent_pause_closes_the_open_interval_once(client, registration, database):
    user, headers = onboard(client, registration)
    subject = create_subject(client, headers).json()
    plan = create_plan(client, headers, subject["id"])
    assert (
        client.post(
            BASE + "/" + str(plan["id"]) + "/start", headers=headers
        ).status_code
        == 200
    )
    barrier = Barrier(2)

    def pause():
        with database.session() as db:
            barrier.wait(timeout=10)
            try:
                StudySessionService(db).pause(user["user"]["id"], plan["id"])
                return "paused"
            except DomainError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: pause(), range(2)))
    assert outcomes.count("paused") == 1
    assert outcomes.count("STUDY_SESSION_TRANSITION_CONFLICT") == 1
    with database.session() as db:
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM study_session_intervals "
                    "WHERE session_id = :session_id AND ended_at IS NOT NULL"
                ),
                {"session_id": plan["id"]},
            )
            == 1
        )
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM study_session_intervals "
                    "WHERE session_id = :session_id AND ended_at IS NULL"
                ),
                {"session_id": plan["id"]},
            )
            == 0
        )


@pytest.mark.parametrize("pg_settings", ["0005_activities"], indirect=True)
def test_upgrade_from_0005_preserves_existing_resources_and_enables_sessions(
    client, registration, database, pg_settings
):
    _, headers = onboard(client, registration)
    subject = create_subject(client, headers).json()
    activity_response = client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            "title": "Ensayo",
            "subject_id": subject["id"],
            "deadline": "2030-02-01T12:00:00Z",
            "priority": "medium",
            "status": "pending",
            "estimated_duration": 30,
            "notes": None,
        },
    )
    assert activity_response.status_code == 201
    order_by = {
        "users": "id",
        "auth_sessions": "id",
        "rate_limit_buckets": "key_hash",
        "user_academic_goal_legacy": "user_id",
        "questionnaire_responses": "user_id, revision",
        "subjects": "id",
        "activities": "id",
        "activity_deadline_events": "activity_id, revision",
    }
    with database.session() as db:
        before = {
            table: db.execute(text(f"SELECT * FROM {table} ORDER BY {columns}")).all()
            for table, columns in order_by.items()
        }
        assert (
            db.scalar(text("SELECT version_num FROM alembic_version"))
            == "0005_activities"
        )
    assert client.get("/api/v1/ready").status_code == 503

    migrate_test_schema(
        database_checkout(), pg_settings.database_url.get_secret_value()
    )
    assert client.get("/api/v1/ready").json() == {"status": "ready"}
    with database.session() as db:
        assert (
            db.scalar(text("SELECT version_num FROM alembic_version"))
            == "0006_study_sessions"
        )
        after = {
            table: db.execute(text(f"SELECT * FROM {table} ORDER BY {columns}")).all()
            for table, columns in order_by.items()
        }
    assert after == before
    created = create_plan(
        client, headers, subject["id"], activity_response.json()["id"]
    )
    assert created["activity_id"] == activity_response.json()["id"]
