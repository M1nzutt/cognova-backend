from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from app.core.domain_error import DomainError
from app.database.dependencies import get_session
from app.schemas.activity_deadline_request import ActivityDeadlineRequest
from app.schemas.activity_write import ActivityWrite
from app.services.activity_service import ActivityService
from app.services.subject_service import SubjectService
from app.tests.database_tooling import database_checkout, migrate_test_schema
from app.tests.integration.test_activities import BASE, setup_activity
from app.tests.integration.test_subjects import create as create_subject
from app.tests.integration.test_subjects import onboard
from app.tests.test_activity_schemas import PAYLOAD


@pytest.mark.parametrize("pg_settings", ["0004_subjects"], indirect=True)
def test_upgrade_0004_preserves_all_existing_data(
    client, registration, database, pg_settings
):
    _, headers = onboard(client, registration)
    subject = create_subject(client, headers).json()
    tables = (
        "users",
        "subjects",
        "auth_sessions",
        "rate_limit_buckets",
        "questionnaire_responses",
        "user_academic_goal_legacy",
    )
    with database.session() as db:
        before = {t: db.execute(text(f"SELECT * FROM {t}")).all() for t in tables}
    assert client.get("/api/v1/ready").status_code == 503
    migrate_test_schema(
        database_checkout(), pg_settings.database_url.get_secret_value()
    )
    assert client.get("/api/v1/ready").status_code == 200
    with database.session() as db:
        for t, rows in before.items():
            assert db.execute(text(f"SELECT * FROM {t}")).all() == rows
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert (
        client.post(
            BASE, headers=headers, json={**PAYLOAD, "subject_id": subject["id"]}
        ).status_code
        == 201
    )


def test_future_dependency_blocks_delete_without_losing_activity(
    client, registration, database
):
    _, headers, _, record = setup_activity(client, registration)
    with database.session() as db:
        db.execute(
            text(
                "CREATE TABLE test_future_dependency ("
                "activity_id integer REFERENCES activities(id) ON DELETE RESTRICT)"
            )
        )
        db.execute(
            text("INSERT INTO test_future_dependency VALUES (:id)"),
            {"id": record["id"]},
        )
        db.commit()
    path = BASE + "/" + str(record["id"])
    response = client.delete(path + "?confirm=true", headers=headers)
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "ACTIVITY_HAS_DEPENDENCIES"
    )
    assert client.get(path, headers=headers).json() == record


@pytest.mark.parametrize("state", ["40001", "40P01"])
def test_retry_after_actual_postgres_abort_preserves_one_event(
    client, registration, database, monkeypatch, state
):
    user, _, _, record = setup_activity(client, registration)
    with database.session() as db:
        original = db.flush
        attempts = 0

        def fail_once(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                db.execute(
                    text(
                        f"DO $$ BEGIN RAISE EXCEPTION 'test retry' "
                        f"USING ERRCODE='{state}'; END $$"
                    )
                )
            return original(*args, **kwargs)

        monkeypatch.setattr(db, "flush", fail_once)
        result = ActivityService(db).set_deadline(
            user["user"]["id"],
            record["id"],
            ActivityDeadlineRequest(
                deadline="2030-02-01T00:00:00Z", expected_revision=0
            ),
        )
        assert result.deadline_revision == 1 and attempts >= 2
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM activity_deadline_events")) == 1


def test_subject_delete_and_activity_create_are_serialized(
    client, registration, database
):
    user, headers = onboard(client, registration)
    sid = create_subject(client, headers).json()["id"]
    uid = user["user"]["id"]
    barrier = Barrier(2)

    def mutate(kind):
        with database.session() as db:
            barrier.wait(timeout=10)
            try:
                if kind == "create":
                    ActivityService(db).create(
                        uid, ActivityWrite(**{**PAYLOAD, "subject_id": sid})
                    )
                else:
                    SubjectService(db).delete(uid, sid)
                return kind
            except DomainError as e:
                return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = set(pool.map(mutate, ["create", "delete"]))
    assert outcomes in (
        {"create", "SUBJECT_HAS_DEPENDENCIES"},
        {"delete", "SUBJECT_NOT_FOUND"},
    )
    with database.session() as db:
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM activities a "
                    "LEFT JOIN subjects s ON a.subject_id=s.id WHERE s.id IS NULL"
                )
            )
            == 0
        )


def test_runtime_least_privilege_history_and_http_permission_failure(
    client, registration, database
):
    _, headers, payload, record = setup_activity(client, registration)
    role = "test_activity_" + uuid4().hex
    with database.session() as admin:
        schema = admin.scalar(text("SELECT current_schema()"))
        assert schema.startswith("test_")
        admin.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
        admin.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
        admin.execute(text(f'GRANT SELECT, UPDATE ON users TO "{role}"'))
        admin.execute(
            text(
                "GRANT SELECT ON subjects, activity_deadline_events, auth_sessions, "
                f'questionnaire_responses, user_academic_goal_legacy TO "{role}"'
            )
        )
        admin.execute(
            text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON activities TO "{role}"')
        )
        admin.execute(
            text(f'GRANT USAGE, SELECT ON SEQUENCE activities_id_seq TO "{role}"')
        )
        admin.commit()

    def restricted():
        with database.session() as db:
            event.listen(
                db,
                "after_begin",
                lambda session, transaction, connection: connection.execute(
                    text(f'SET LOCAL ROLE "{role}"')
                ),
            )
            yield db

    try:
        client.app.dependency_overrides[get_session] = restricted
        created = client.post(BASE, headers=headers, json=payload)
        assert created.status_code == 201
        path = BASE + "/" + str(created.json()["id"])
        changed = client.patch(
            path + "/deadline",
            headers=headers,
            json={"deadline": "2030-02-01T00:00:00Z", "expected_revision": 0},
        )
        assert changed.status_code == 200 and changed.json()["deadline_revision"] == 1
        assert (
            len(client.get(path + "/deadline-history", headers=headers).json()["items"])
            == 1
        )
        blocked = client.delete(path + "?confirm=true", headers=headers)
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()["error"]["code"] == "ACTIVITY_HAS_DEPENDENCIES"
        fresh = client.post(BASE, headers=headers, json=payload).json()
        fresh_path = BASE + "/" + str(fresh["id"])
        assert (
            client.delete(fresh_path + "?confirm=true", headers=headers).status_code
            == 204
        )
        with database.session() as admin:
            admin.execute(text(f'REVOKE DELETE ON activities FROM "{role}"'))
            admin.commit()
        original_path = BASE + "/" + str(record["id"])
        failed = client.delete(original_path + "?confirm=true", headers=headers)
        assert (
            failed.status_code == 503
            and failed.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
        )
        assert "42501" not in failed.text
        assert client.get(original_path, headers=headers).json() == record
        assert failed.headers["cache-control"] == "no-store"
        for sql in (
            "INSERT INTO activity_deadline_events "
            "SELECT * FROM activity_deadline_events",
            "UPDATE activity_deadline_events SET revision=2",
            "DELETE FROM activity_deadline_events",
            "TRUNCATE activity_deadline_events",
            "ALTER TABLE activities ADD COLUMN test_bad int",
            "UPDATE alembic_version SET version_num='bad'",
            "SELECT cognova_record_activity_deadline()",
        ):
            with database.session() as db:
                db.execute(text(f'SET LOCAL ROLE "{role}"'))
                with pytest.raises(DBAPIError) as error:
                    db.execute(text(sql))
                assert error.value.orig.sqlstate == "42501"
                db.rollback()
    finally:
        client.app.dependency_overrides.pop(get_session, None)
        with database.session() as admin:
            admin.execute(text(f'DROP OWNED BY "{role}"'))
            admin.execute(text(f'DROP ROLE "{role}"'))
            admin.commit()


def test_history_failure_rolls_back_http_update(client, registration, database):
    _, headers, _, record = setup_activity(client, registration)
    with database.session() as db:
        db.execute(
            text(
                "ALTER TABLE activity_deadline_events ADD CONSTRAINT "
                "test_block_event CHECK (revision < 0) NOT VALID"
            )
        )
        db.commit()
    path = BASE + "/" + str(record["id"])
    failed = client.patch(
        path + "/deadline",
        headers=headers,
        json={"deadline": "2030-02-01T00:00:00Z", "expected_revision": 0},
    )
    assert failed.status_code == 503
    assert client.get(path, headers=headers).json() == record
    assert client.get(path + "/deadline-history", headers=headers).json()["items"] == []
