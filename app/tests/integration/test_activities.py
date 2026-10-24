from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import text

from app.core.domain_error import DomainError
from app.schemas.activity_deadline_request import ActivityDeadlineRequest
from app.services.activity_service import ActivityService
from app.tests.integration.test_subjects import create as create_subject
from app.tests.integration.test_subjects import onboard
from app.tests.test_activity_schemas import PAYLOAD

BASE = "/api/v1/activities"


def setup_activity(client, registration):
    user, headers = onboard(client, registration)
    subject = create_subject(client, headers).json()
    payload = {**PAYLOAD, "subject_id": subject["id"]}
    response = client.post(BASE, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return user, headers, payload, response.json()


def test_crud_history_and_dependency_retention(client, registration, database):
    _, headers, payload, original = setup_activity(client, registration)
    path = BASE + "/" + str(original["id"])
    assert "user_id" not in original
    assert original["original_deadline"] == original["deadline"]
    assert original["deadline_revision"] == 0
    assert client.get(path, headers=headers).json() == original
    assert client.get(BASE, headers=headers).json()["items"] == [original]
    edited = client.put(
        path,
        headers=headers,
        json={**payload, "title": "  Física  ", "notes": "Apuntes"},
    )
    assert edited.status_code == 200 and edited.json()["title"] == "Física"
    assert edited.json()["created_at"] == original["created_at"]
    assert edited.json()["updated_at"] >= original["updated_at"]
    for revision, deadline, event_type in [
        (0, "2030-01-03T12:00:00Z", "postponed"),
        (1, "2030-01-02T12:00:00Z", "rescheduled"),
        (2, "2030-01-04T12:00:00Z", "postponed"),
    ]:
        response = client.patch(
            path + "/deadline",
            headers=headers,
            json={"deadline": deadline, "expected_revision": revision},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "pending"
        assert response.json()["original_deadline"] == original["deadline"]
        history = client.get(path + "/deadline-history", headers=headers).json()[
            "items"
        ]
        assert len(history) == revision + 1 and history[-1]["event_type"] == event_type
    history = client.get(path + "/deadline-history?limit=2", headers=headers).json()
    assert history["next_after_revision"] == 2
    last = client.get(
        path + "/deadline-history?after_revision=2", headers=headers
    ).json()
    assert last["items"][0]["revision"] == 3 and last["next_after_revision"] is None
    same = client.patch(
        path + "/deadline",
        headers=headers,
        json={"deadline": "2030-01-04T07:00:00-05:00", "expected_revision": 3},
    )
    assert same.json()["deadline_revision"] == 3
    stale = client.patch(
        path + "/deadline",
        headers=headers,
        json={"deadline": payload["deadline"], "expected_revision": 0},
    )
    assert (
        stale.status_code == 409
        and stale.json()["error"]["code"] == "ACTIVITY_DEADLINE_CONFLICT"
    )
    subject_path = "/api/v1/subjects/" + str(payload["subject_id"])
    assert client.post(subject_path + "/archive", headers=headers).status_code == 200
    assert client.get(path, headers=headers).status_code == 200
    blocked = client.delete(subject_path + "?confirm=true", headers=headers)
    assert (
        blocked.status_code == 409
        and blocked.json()["error"]["code"] == "SUBJECT_HAS_DEPENDENCIES"
    )
    blocked = client.delete(path + "?confirm=true", headers=headers)
    assert (
        blocked.status_code == 409
        and blocked.json()["error"]["code"] == "ACTIVITY_HAS_DEPENDENCIES"
    )
    assert client.get(path, headers=headers).status_code == 200
    # Archived subjects can also receive new activities. No history: DELETE succeeds.
    fresh = client.post(BASE, headers=headers, json=payload)
    assert fresh.status_code == 201
    fresh_path = BASE + "/" + str(fresh.json()["id"])
    for suffix in ("", "?confirm=false", "?confirm=1"):
        assert client.delete(fresh_path + suffix, headers=headers).status_code == 422
    assert (
        client.delete(fresh_path + "?confirm=true", headers=headers).status_code == 204
    )
    assert client.get(fresh_path, headers=headers).status_code == 404
    assert (
        client.delete(fresh_path + "?confirm=true", headers=headers).status_code == 404
    )
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM activity_deadline_events")) == 3
        assert db.scalar(text("SELECT count(*) FROM activities")) == 1


def test_status_and_put_share_transition_rules_and_atomicity(client, registration):
    _, headers, payload, original = setup_activity(client, registration)
    path = BASE + "/" + str(original["id"])
    completed = client.patch(
        path + "/status",
        headers=headers,
        json={"status": "completed", "expected_status": "pending"},
    )
    assert completed.status_code == 200
    same = client.patch(
        path + "/status",
        headers=headers,
        json={"status": "completed", "expected_status": "completed"},
    )
    assert same.json() == completed.json()
    conflict = client.patch(
        path + "/status",
        headers=headers,
        json={"status": "pending", "expected_status": "pending"},
    )
    assert (
        conflict.status_code == 409
        and conflict.json()["error"]["code"] == "ACTIVITY_STATE_CONFLICT"
    )
    blocked = client.put(
        path,
        headers=headers,
        json={**payload, "status": "in_progress", "deadline": "2030-02-01T00:00:00Z"},
    )
    assert (
        blocked.status_code == 409
        and blocked.json()["error"]["code"] == "ACTIVITY_TRANSITION_CONFLICT"
    )
    assert client.get(path + "/deadline-history", headers=headers).json()["items"] == []
    reopened = client.put(
        path,
        headers=headers,
        json={**payload, "status": "pending", "deadline": "2030-02-01T00:00:00Z"},
    )
    assert reopened.status_code == 200 and reopened.json()["deadline_revision"] == 1
    postponed = client.patch(
        path + "/status",
        headers=headers,
        json={"status": "postponed", "expected_status": "pending"},
    )
    assert postponed.status_code == 200 and postponed.json()["deadline_revision"] == 1


def test_ownership_every_route_and_subject_assignment(client, registration, database):
    _, owner, payload, original = setup_activity(client, registration)
    _, other = onboard(client, {**registration, "email": "other@example.com"})
    other_subject = create_subject(client, other, "Ajena").json()["id"]
    path = BASE + "/" + str(original["id"])
    calls = [
        ("get", path, None),
        ("get", path + "/deadline-history", None),
        ("put", path, payload),
        (
            "patch",
            path + "/status",
            {"status": "completed", "expected_status": "pending"},
        ),
        (
            "patch",
            path + "/deadline",
            {"deadline": "2030-02-01T00:00:00Z", "expected_revision": 0},
        ),
        ("delete", path + "?confirm=true", None),
    ]
    for method, url, body in calls:
        kwargs = {"json": body} if body is not None else {}
        foreign = client.request(method, url, headers=other, **kwargs)
        missing = client.request(
            method,
            url.replace(path, BASE + "/2147483647", 1),
            headers=other,
            **kwargs,
        )
        assert foreign.status_code == 404 and foreign.json() == missing.json()
        assert foreign.headers["cache-control"] == "no-store"
    assert client.get(BASE, headers=other).json()["items"] == []
    for sid in (other_subject, 2147483647):
        for method, url in (("post", BASE), ("put", path)):
            response = client.request(
                method, url, headers=owner, json={**payload, "subject_id": sid}
            )
            assert (
                response.status_code == 404
                and response.json()["error"]["code"] == "SUBJECT_NOT_FOUND"
            )
    assert client.get(path, headers=owner).json() == original
    assert (
        client.get(BASE, headers=owner, params={"subject_id": other_subject}).json()[
            "items"
        ]
        == []
    )
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM activities")) == 1


def test_filters_pagination_validation_and_no_store(client, registration):
    _, headers, payload, original = setup_activity(client, registration)
    for priority, day in [("high", 2), ("urgent", 3)]:
        assert (
            client.post(
                BASE,
                headers=headers,
                json={
                    **payload,
                    "priority": priority,
                    "deadline": f"2030-01-0{day}T12:00:00Z",
                },
            ).status_code
            == 201
        )
    params = {
        "subject_id": payload["subject_id"],
        "status": "pending",
        "priority": "high",
        "deadline_from": "2030-01-02T12:00:00Z",
        "deadline_to": "2030-01-02T12:00:00Z",
    }
    filtered = client.get(BASE, headers=headers, params=params)
    assert filtered.status_code == 200 and len(filtered.json()["items"]) == 1
    assert filtered.json()["items"][0]["priority"] == "high"
    exact = client.get(
        BASE, headers=headers, params={"deadline": "2030-01-01T07:00:00-05:00"}
    )
    assert exact.json()["items"] == [original]
    first = client.get(BASE, headers=headers, params={"limit": 2}).json()
    second = client.get(
        BASE, headers=headers, params={"limit": 2, "after_id": first["next_after_id"]}
    ).json()
    assert (
        len(first["items"]) + len(second["items"]) == 3
        and second["next_after_id"] is None
    )
    for params in (
        {"status": "done"},
        {"limit": 101},
        {"subject_id": 0},
        {"after_id": -1},
        {"deadline": "2030-01-01"},
        {
            "deadline_from": "2030-02-01T00:00:00Z",
            "deadline_to": "2030-01-01T00:00:00Z",
        },
    ):
        response = client.get(BASE, headers=headers, params=params)
        assert (
            response.status_code == 422
            and response.headers["cache-control"] == "no-store"
        )


def test_auth_onboarding_and_csrf_unchanged(client, registration):
    assert client.get(BASE).status_code == 401
    response = client.post("/api/v1/auth/register", json=registration)
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.get(BASE, headers=headers).status_code == 403
    assert client.post("/api/v1/auth/refresh").status_code == 403
    assert client.post("/api/v1/auth/logout").status_code == 403


def test_concurrent_deadline_precondition_allows_one_event(
    client, registration, database
):
    user, headers, payload, original = setup_activity(client, registration)
    barrier = Barrier(2)

    def change(day):
        with database.session() as db:
            barrier.wait(timeout=10)
            try:
                result = ActivityService(db).set_deadline(
                    user["user"]["id"],
                    original["id"],
                    ActivityDeadlineRequest(
                        deadline=f"2030-01-0{day}T12:00:00Z", expected_revision=0
                    ),
                )
                return result.deadline_revision
            except DomainError as e:
                return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(change, [2, 3]))
    assert sorted(map(str, outcomes)) == ["1", "ACTIVITY_DEADLINE_CONFLICT"]
    with database.session() as db:
        assert db.scalar(text("SELECT count(*) FROM activity_deadline_events")) == 1
