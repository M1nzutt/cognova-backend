from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.models.subject import Subject
from app.schemas.subject_create import SubjectCreate
from app.services.subject_service import SubjectService
from app.tests.integration.test_onboarding import authenticate
from app.tests.questionnaire_samples import questionnaire_payload
from app.tests.test_subject_schemas import PAYLOAD

BASE = "/api/v1/subjects"


def onboard(client, registration):
    result, headers = authenticate(client, registration)
    assert (
        client.put(
            "/api/v1/onboarding/academic-profile",
            headers=headers,
            json={"degree_program": "Software", "semester": 1},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/questionnaire", headers=headers, json=questionnaire_payload()
        ).status_code
        == 201
    )
    return result, headers


def create(client, headers, name="Matemáticas", **kwargs):
    return client.post(BASE, headers=headers, json={**PAYLOAD, "name": name, **kwargs})


def test_full_lifecycle_and_archive_identity(client, registration, database):
    _, headers = onboard(client, registration)
    catalog = client.get(BASE + "/catalog", headers=headers)
    assert catalog.status_code == 200
    assert catalog.json()["version"] == 1
    assert len(catalog.json()["color_bases"]) == 10
    response = create(client, headers, "  Matemáticas  ")
    assert response.status_code == 201
    original = response.json()
    path = BASE + "/" + str(original["id"])
    assert original["name"] == "Matemáticas"
    assert "user_id" not in original and "active_slot" not in original
    assert client.get(path, headers=headers).json() == original
    edited = client.put(
        path,
        headers=headers,
        json={**PAYLOAD, "name": "Física", "difficulty": "hard", "color_base": "teal"},
    )
    assert edited.status_code == 200 and edited.json()["name"] == "Física"
    assert edited.json()["created_at"] == original["created_at"]
    assert edited.json()["updated_at"] != original["updated_at"]
    archived = client.post(path + "/archive", headers=headers)
    assert archived.json()["status"] == "archived"
    assert client.post(path + "/archive", headers=headers).json() == archived.json()
    assert client.get(BASE, headers=headers).json()["items"] == []
    assert (
        len(client.get(BASE + "?status=archived", headers=headers).json()["items"]) == 1
    )
    restored = client.post(path + "/reactivate", headers=headers)
    assert restored.json()["status"] == "active"
    assert restored.json()["id"] == original["id"]
    assert client.post(path + "/reactivate", headers=headers).json() == restored.json()
    for query in ("", "?confirm=false", "?confirm=1"):
        assert client.delete(path + query, headers=headers).status_code == 422
    assert client.delete(path + "?confirm=true", headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path + "?confirm=true", headers=headers).status_code == 404
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM questionnaire_responses")) == 1


def test_limit_duplicate_names_and_reactivation_without_room(client, registration):
    _, headers = onboard(client, registration)
    active = [create(client, headers, f"Materia {i}").json() for i in range(5)]
    assert (
        create(client, headers, "Sexta").json()["error"]["code"]
        == "SUBJECT_ACTIVE_LIMIT"
    )
    archived = create(client, headers, "Archivo", status="archived")
    assert archived.status_code == 201
    assert create(client, headers, "ARCHIVO", status="archived").json()["error"][
        "code"
    ] == ("SUBJECT_NAME_CONFLICT")
    path = BASE + "/" + str(archived.json()["id"])
    failed = client.post(path + "/reactivate", headers=headers)
    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "SUBJECT_REACTIVATION_LIMIT"
    assert client.get(path, headers=headers).json()["status"] == "archived"
    rename = client.put(path, headers=headers, json={**PAYLOAD, "name": "MATERIA 0"})
    assert rename.status_code == 409
    assert client.get(path, headers=headers).json()["name"] == "Archivo"
    assert (
        client.post(BASE + f"/{active[0]['id']}/archive", headers=headers).status_code
        == 200
    )
    assert client.post(path + "/reactivate", headers=headers).status_code == 200
    for i in range(6):
        assert (
            create(client, headers, f"Archivo {i}", status="archived").status_code
            == 201
        )


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "", None),
        ("PUT", "", PAYLOAD),
        ("DELETE", "?confirm=true", None),
        ("POST", "/archive", None),
        ("POST", "/reactivate", None),
    ],
)
def test_foreign_subject_is_indistinguishable_from_missing(
    client, registration, method, suffix, body
):
    _, owner = onboard(client, registration)
    _, other = onboard(client, {**registration, "email": "other@example.com"})
    row = create(client, owner).json()
    foreign = client.request(
        method, BASE + f"/{row['id']}" + suffix, headers=other, json=body
    )
    missing = client.request(
        method, BASE + "/2147483647" + suffix, headers=other, json=body
    )
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    assert client.get(BASE, headers=other).json()["items"] == []
    assert create(client, other).status_code == 201  # Same name, different owner.
    assert client.get(BASE + f"/{row['id']}", headers=owner).json() == row


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", BASE, None),
        ("GET", BASE + "/catalog", None),
        ("POST", BASE, PAYLOAD),
        ("GET", BASE + "/1", None),
        ("PUT", BASE + "/1", PAYLOAD),
        ("DELETE", BASE + "/1?confirm=true", None),
        ("POST", BASE + "/1/archive", None),
        ("POST", BASE + "/1/reactivate", None),
    ],
)
def test_auth_and_onboarding_gate_all_routes(client, registration, method, path, body):
    assert client.request(method, path, json=body).status_code == 401
    _, headers = authenticate(client, registration)
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ONBOARDING_REQUIRED"


def test_filters_cursor_and_no_store(client, registration):
    _, headers = onboard(client, registration)
    ids = [
        create(client, headers, f"Row {i}", status="archived").json()["id"]
        for i in range(3)
    ]
    page = client.get(BASE + "?status=archived&limit=2", headers=headers)
    assert page.headers["cache-control"] == "no-store"
    assert [row["id"] for row in page.json()["items"]] == ids[:2]
    next_id = page.json()["next_after_id"]
    last = client.get(
        BASE + f"?status=archived&after_id={next_id}", headers=headers
    ).json()
    assert [row["id"] for row in last["items"]] == ids[2:]
    assert last["next_after_id"] is None
    for query in ("limit=0", "limit=101", "status=bad", "after_id=-1"):
        assert client.get(BASE + "?" + query, headers=headers).status_code == 422
    assert len(client.get(BASE + "?status=all", headers=headers).json()["items"]) == 3


def test_dependencies_block_delete_and_preserve_every_row(
    client, registration, database
):
    _, headers = onboard(client, registration)
    row = create(client, headers).json()
    with database.session() as db:
        # Test-only future dependency in the disposable schema; no production DDL.
        db.execute(
            text(
                "CREATE TABLE subject_test_reference "
                "(subject_id integer REFERENCES subjects(id) ON DELETE RESTRICT)"
            )
        )
        db.execute(
            text("INSERT INTO subject_test_reference VALUES (:id)"), {"id": row["id"]}
        )
        db.commit()
    result = client.delete(BASE + f"/{row['id']}?confirm=true", headers=headers)
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "SUBJECT_HAS_DEPENDENCIES"
    assert client.get(BASE + f"/{row['id']}", headers=headers).json() == row
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM subject_test_reference")) == 1


@pytest.mark.parametrize("reactivate", [False, True])
def test_two_writers_compete_for_last_slot(client, registration, database, reactivate):
    _, headers = onboard(client, registration)
    for i in range(4):
        assert create(client, headers, f"Active {i}").status_code == 201
    archived = [
        create(client, headers, f"Archived {i}", status="archived").json()["id"]
        for i in range(2)
    ]
    barrier = Barrier(2)

    # Avoid entering a second lifespan on the same app.
    def request(i):
        worker = TestClient(client.app, base_url="https://testserver")
        try:
            barrier.wait(timeout=10)
            return (
                worker.post(BASE + f"/{archived[i]}/reactivate", headers=headers)
                if reactivate
                else create(worker, headers, f"Concurrent {i}")
            )
        finally:
            worker.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(request, range(2)))
    assert sorted(r.status_code for r in responses) == [200 if reactivate else 201, 409]
    with database.session() as db:
        assert (
            db.scalar(text("SELECT count(*) FROM subjects WHERE status='active'")) == 5
        )


def test_mutation_replaces_stale_snapshot_with_read_committed(
    client, registration, database
):
    result, _ = onboard(client, registration)
    uid = result["user"]["id"]
    with database.session() as stale:
        stale.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        assert stale.scalars(select(Subject)).all() == []  # Establish old snapshot.
        with database.session() as fresh:
            SubjectService(fresh).create(uid, SubjectCreate(**PAYLOAD))
        created = SubjectService(stale).create(
            uid, SubjectCreate(**{**PAYLOAD, "name": "Second"})
        )
        assert created.name == "Second"
    with database.session() as db:
        assert sorted(db.scalars(select(Subject.active_slot)).all()) == [1, 2]


def test_api_boundaries_and_forbidden_fields(client, registration):
    _, headers = onboard(client, registration)
    assert create(client, headers, "🚀" * 20).status_code == 201
    for overrides in (
        {"name": "🚀" * 21},
        {"user_id": 99},
        {"active_slot": 2},
        {"color_shade": 300.0},
        {"color_base": "#fff"},
        {"difficulty": "Fácil"},
    ):
        response = client.post(BASE, headers=headers, json={**PAYLOAD, **overrides})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    row = create(client, headers, "Cafe\u0301").json()
    assert row["name"] == "Café"
    assert (
        create(client, headers, "CAFÉ").json()["error"]["code"]
        == "SUBJECT_NAME_CONFLICT"
    )


def test_concurrent_duplicate_name_is_one_conflict(client, registration):
    _, headers = onboard(client, registration)
    barrier = Barrier(2)

    def request(name):
        worker = TestClient(client.app, base_url="https://testserver")
        try:
            barrier.wait(timeout=10)
            return create(worker, headers, name, status="archived")
        finally:
            worker.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(request, ("álgebra", "ÁLGEBRA")))
    assert sorted(r.status_code for r in responses) == [201, 409]
    conflict = next(r for r in responses if r.status_code == 409)
    assert conflict.json()["error"]["code"] == "SUBJECT_NAME_CONFLICT"


@pytest.mark.parametrize(
    "pg_settings", ["0003_onboarding_questionnaire"], indirect=True
)
def test_upgrade_from_0003_preserves_auth_onboarding(
    client, registration, database, pg_settings
):
    from app.tests.database_tooling import database_checkout, migrate_test_schema

    _, headers = onboard(client, registration)
    tables = (
        "users",
        "auth_sessions",
        "rate_limit_buckets",
        "user_academic_goal_legacy",
        "questionnaire_responses",
    )
    with database.session() as db:
        before = {
            table: db.execute(text(f"SELECT * FROM {table}")).all() for table in tables
        }
    assert client.get("/api/v1/ready").status_code == 503
    migrate_test_schema(
        database_checkout(), pg_settings.database_url.get_secret_value()
    )
    assert client.get("/api/v1/ready").status_code == 200
    with database.session() as db:
        for table, rows in before.items():
            assert db.execute(text(f"SELECT * FROM {table}")).all() == rows
    assert create(client, headers).status_code == 201


@pytest.mark.parametrize("state", ["40001", "40P01"])
def test_retry_after_real_postgresql_transaction_abort(
    client, registration, database, monkeypatch, state
):
    result, _ = onboard(client, registration)
    with database.session() as db:
        original_flush = db.flush
        attempts = 0

        def abort_once(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                # Fail inside PostgreSQL, leaving the transaction aborted.
                db.execute(
                    text(
                        "DO $$ BEGIN RAISE EXCEPTION 'test-only retry' "
                        f"USING ERRCODE = '{state}'; END $$"
                    )
                )
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", abort_once)
        record = SubjectService(db).create(
            result["user"]["id"], SubjectCreate(**PAYLOAD)
        )
        assert attempts >= 2 and record.name == PAYLOAD["name"]
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM subjects")) == 1


def test_retry_after_actual_slot_unique_violation(
    client, registration, database, monkeypatch
):
    result, _ = onboard(client, registration)
    uid = result["user"]["id"]
    with database.session() as db:
        service = SubjectService(db)
        service.create(uid, SubjectCreate(**PAYLOAD))
        original_slot = service._slot
        attempts = 0

        def conflict_once(user_id, **kwargs):
            nonlocal attempts
            attempts += 1
            return 1 if attempts == 1 else original_slot(user_id, **kwargs)

        monkeypatch.setattr(service, "_slot", conflict_once)
        service.create(uid, SubjectCreate(**{**PAYLOAD, "name": "Second"}))
        assert attempts == 2
    with database.session() as db:
        assert sorted(db.scalars(select(Subject.active_slot)).all()) == [1, 2]
