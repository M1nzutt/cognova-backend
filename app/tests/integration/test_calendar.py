from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_onboarding import authenticate
from app.tests.integration.test_study_sessions import create_plan
from app.tests.integration.test_subjects import create, onboard
from app.tests.test_calendar import WINDOW

BASE = "/api/v1/calendar"


def get(client, headers, **params):
    response = client.get(BASE, headers=headers, params={**WINDOW, **params})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def snapshot(database):
    with database.session() as db:
        return [
            db.execute(text("SELECT * FROM " + table + " ORDER BY 1,2")).all()
            for table in (
                "activities",
                "activity_deadline_events",
                "subjects",
                "study_sessions",
                "study_session_intervals",
            )
        ]


def test_calendar_boundaries_order_pagination_filters_and_read_only(
    client, registration, database
):
    _, headers, payload, initial = setup_activity(client, registration)
    other = create(client, headers, name="Otra").json()
    records = []
    for deadline, subject, status, priority in [
        ("2030-01-31T23:59:59.999999Z", payload["subject_id"], "completed", "high"),
        ("2030-01-01T00:00:00Z", payload["subject_id"], "pending", "urgent"),
        ("2030-01-01T00:00:00Z", other["id"], "cancelled", "low"),
        ("2030-02-01T00:00:00Z", other["id"], "pending", "medium"),
        ("2029-12-31T23:59:59.999999Z", other["id"], "pending", "medium"),
    ]:
        r = client.post(
            "/api/v1/activities",
            headers=headers,
            json={
                **payload,
                "subject_id": subject,
                "deadline": deadline,
                "status": status,
                "priority": priority,
            },
        )
        assert r.status_code == 201
        records.append(r.json())
    assert (
        client.post(
            f"/api/v1/subjects/{other['id']}/archive", headers=headers
        ).status_code
        == 200
    )
    before = snapshot(database)
    expected = [records[1]["id"], records[2]["id"], initial["id"], records[0]["id"]]
    first = get(client, headers, limit=1)
    collected = first["items"][:]
    while first["next_cursor"]:
        first = get(client, headers, limit=1, **first["next_cursor"])
        collected += first["items"]
    assert [r["id"] for r in collected] == expected
    assert all(r["type"] == "activity" for r in collected)
    activity_type = get(client, headers, type="activity")
    assert [item["id"] for item in activity_type["items"]] == expected
    assert all(item["type"] == "activity" for item in activity_type["items"])
    assert "user_id" not in collected[0] and "notes" not in collected[0]
    assert len(get(client, headers, subject_id=other["id"])["items"]) == 1
    for key, value, expected_id in [
        ("status", "completed", records[0]["id"]),
        ("priority", "urgent", records[1]["id"]),
    ]:
        assert [r["id"] for r in get(client, headers, **{key: value})["items"]] == [
            expected_id
        ]
    assert (
        get(
            client, headers, subject_id=other["id"], status="completed", priority="high"
        )["items"]
        == []
    )
    assert get(client, headers, subject_id=2147483647) == {
        "items": [],
        "next_cursor": None,
    }
    offset = get(
        client,
        headers,
        deadline_from="2029-12-31T19:00:00-05:00",
        deadline_to="2030-01-31T19:00:00-05:00",
    )
    assert [r["id"] for r in offset["items"]] == expected
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(BASE, headers=headers).status_code == 405
    assert snapshot(database) == before


def test_original_activity_mutations_are_reflected_without_calendar_writes(
    client, registration, database
):
    _, headers, payload, initial = setup_activity(client, registration)
    path = f"/api/v1/activities/{initial['id']}"
    for revision, deadline in [
        (0, "2030-02-02T00:00:00Z"),
        (1, "2030-01-02T00:00:00Z"),
    ]:
        assert (
            client.patch(
                path + "/deadline",
                headers=headers,
                json={"deadline": deadline, "expected_revision": revision},
            ).status_code
            == 200
        )
        items = get(client, headers)["items"]
        if revision == 0:
            assert items == []
        else:
            assert items[0]["original_deadline"] == initial["original_deadline"]
            assert items[0]["deadline"] != items[0]["original_deadline"]
    history = client.get(path + "/deadline-history", headers=headers).json()["items"]
    assert [h["event_type"] for h in history] == ["postponed", "rescheduled"]
    fresh = client.post("/api/v1/activities", headers=headers, json=payload).json()
    assert (
        client.delete(
            f"/api/v1/activities/{fresh['id']}?confirm=true", headers=headers
        ).status_code
        == 204
    )
    assert [r["id"] for r in get(client, headers)["items"]] == [initial["id"]]
    before = snapshot(database)
    get(client, headers)
    assert snapshot(database) == before


def test_calendar_only_study_sessions(client, registration):
    _, headers = onboard(client, registration)
    subject = create(client, headers).json()
    first = create_plan(
        client,
        headers,
        subject["id"],
        planned_start_at="2030-01-01T12:00:00Z",
        planned_duration=25,
    )
    second = create_plan(
        client,
        headers,
        subject["id"],
        planned_start_at="2030-01-02T12:00:00Z",
        planned_duration=40,
    )

    response = get(client, headers, type="study_session")
    assert [item["id"] for item in response["items"]] == [first["id"], second["id"]]
    for item, expected in zip(response["items"], (first, second), strict=True):
        assert item == {
            "id": expected["id"],
            "type": "study_session",
            "subject_id": subject["id"],
            "activity_id": None,
            "planned_start_at": expected["planned_start_at"],
            "planned_duration": expected["planned_duration"],
            "lifecycle": "planned",
            "result": None,
            "start_at": None,
            "end_at": None,
        }


def test_calendar_mixed_order_ties_legacy_cursor_and_pagination(
    client, registration, database
):
    _, headers, payload, first_activity = setup_activity(client, registration)
    same_time = first_activity["deadline"]
    second_response = client.post(
        "/api/v1/activities",
        headers=headers,
        json={**payload, "deadline": same_time},
    )
    assert second_response.status_code == 201, second_response.text
    second_activity = second_response.json()
    first_session = create_plan(
        client, headers, payload["subject_id"], planned_start_at=same_time
    )
    second_session = create_plan(
        client, headers, payload["subject_id"], planned_start_at=same_time
    )
    before = snapshot(database)

    page = get(client, headers, limit=1)
    collected = page["items"][:]
    cursor_types = []
    while page["next_cursor"]:
        cursor_types.append(page["next_cursor"]["after_type"])
        page = get(client, headers, limit=1, **page["next_cursor"])
        collected.extend(page["items"])
    assert [(item["type"], item["id"]) for item in collected] == [
        ("activity", first_activity["id"]),
        ("activity", second_activity["id"]),
        ("study_session", first_session["id"]),
        ("study_session", second_session["id"]),
    ]
    assert cursor_types == ["activity", "activity", "study_session"]

    legacy_page = get(
        client,
        headers,
        limit=10,
        after_deadline=same_time,
        after_id=second_activity["id"],
    )
    assert [(item["type"], item["id"]) for item in legacy_page["items"]] == [
        ("study_session", first_session["id"]),
        ("study_session", second_session["id"]),
    ]
    assert snapshot(database) == before


def test_calendar_semi_open_boundaries_cover_both_sources(client, registration):
    _, headers, payload, start_activity = setup_activity(client, registration)
    subject_id = payload["subject_id"]
    start = "2030-01-01T12:00:00Z"
    end = "2030-01-01T13:00:00Z"
    before_time = "2030-01-01T11:59:59.999999Z"
    after_time = end
    before_activity = client.post(
        "/api/v1/activities",
        headers=headers,
        json={**payload, "deadline": before_time},
    ).json()
    end_activity = client.post(
        "/api/v1/activities",
        headers=headers,
        json={**payload, "deadline": after_time},
    ).json()
    before_session = create_plan(
        client, headers, subject_id, planned_start_at=before_time
    )
    start_session = create_plan(client, headers, subject_id, planned_start_at=start)
    end_session = create_plan(client, headers, subject_id, planned_start_at=after_time)

    response = get(client, headers, deadline_from=start, deadline_to=end)["items"]
    assert [(item["type"], item["id"]) for item in response] == [
        ("activity", start_activity["id"]),
        ("study_session", start_session["id"]),
    ]
    identities = [(item["type"], item["id"]) for item in response]
    assert ("activity", before_activity["id"]) not in identities
    assert ("activity", end_activity["id"]) not in identities
    assert ("study_session", before_session["id"]) not in identities
    assert ("study_session", end_session["id"]) not in identities


def test_calendar_type_subject_and_compatible_filters(client, registration):
    _, headers, payload, first_activity = setup_activity(client, registration)
    other_subject = create(client, headers, name="Otra").json()
    second_activity_response = client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            **payload,
            "subject_id": other_subject["id"],
            "deadline": "2030-01-03T12:00:00Z",
            "status": "completed",
            "priority": "urgent",
        },
    )
    assert second_activity_response.status_code == 201
    second_activity = second_activity_response.json()
    first_session = create_plan(
        client,
        headers,
        payload["subject_id"],
        planned_start_at="2030-01-02T12:00:00Z",
    )
    second_session = create_plan(
        client,
        headers,
        other_subject["id"],
        planned_start_at="2030-01-04T12:00:00Z",
    )

    activity_items = get(client, headers, type="activity")["items"]
    session_items = get(client, headers, type="study_session")["items"]
    assert {item["id"] for item in activity_items} == {
        first_activity["id"],
        second_activity["id"],
    }
    assert {item["id"] for item in session_items} == {
        first_session["id"],
        second_session["id"],
    }
    subject_items = get(client, headers, subject_id=other_subject["id"])["items"]
    assert [(item["type"], item["id"]) for item in subject_items] == [
        ("activity", second_activity["id"]),
        ("study_session", second_session["id"]),
    ]
    status_items = get(client, headers, status="completed")["items"]
    assert [(item["type"], item["id"]) for item in status_items] == [
        ("activity", second_activity["id"])
    ]
    priority_items = get(client, headers, priority="urgent")["items"]
    assert [(item["type"], item["id"]) for item in priority_items] == [
        ("activity", second_activity["id"])
    ]
    invalid = client.get(
        BASE,
        headers=headers,
        params={**WINDOW, "type": "study_session", "status": "completed"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("lifecycle", ["planned", "running", "paused", "finished"])
def test_calendar_projects_every_study_session_lifecycle(
    client, registration, lifecycle, monkeypatch
):
    from app.services import study_session_service

    _, headers = onboard(client, registration)
    subject = create(client, headers).json()
    clock = {"now": datetime(2035, 1, 1, tzinfo=timezone.utc)}
    monkeypatch.setattr(study_session_service, "utc_now", lambda: clock["now"])
    planned_start = "2030-01-02T12:00:00Z"
    session = create_plan(
        client, headers, subject["id"], planned_start_at=planned_start
    )
    path = f"/api/v1/sessions/{session['id']}"
    if lifecycle != "planned":
        started = client.post(path + "/start", headers=headers)
        assert started.status_code == 200, started.text
    if lifecycle in {"paused", "finished"}:
        clock["now"] += timedelta(seconds=10)
        if lifecycle == "paused":
            paused = client.post(path + "/pause", headers=headers)
            assert paused.status_code == 200, paused.text
        else:
            finished = client.post(
                path + "/finish", headers=headers, json={"status": "completed"}
            )
            assert finished.status_code == 200, finished.text

    response = get(client, headers, type="study_session")
    assert len(response["items"]) == 1
    item = response["items"][0]
    assert item["planned_start_at"] == session["planned_start_at"]
    assert item["lifecycle"] == lifecycle
    if lifecycle == "planned":
        assert item["result"] is None
        assert item["start_at"] is None and item["end_at"] is None
    elif lifecycle == "running":
        assert item["result"] is None
        assert item["start_at"] is not None and item["end_at"] is None
    elif lifecycle == "paused":
        assert item["result"] is None
        assert item["start_at"] is not None and item["end_at"] is None
    else:
        assert item["result"] == "completed"
        assert item["start_at"] is not None and item["end_at"] is not None


def test_calendar_authorization_and_invalid_queries(client, registration):
    assert client.get(BASE, params=WINDOW).status_code == 401
    _, incomplete = authenticate(client, registration)
    assert client.get(BASE, headers=incomplete, params=WINDOW).status_code == 403
    _, owner, payload, activity = setup_activity(
        client, {**registration, "email": "owner@example.com"}
    )
    session = create_plan(
        client,
        owner,
        payload["subject_id"],
        activity["id"],
        planned_start_at="2030-01-03T12:00:00Z",
    )
    _, stranger = onboard(client, {**registration, "email": "stranger@example.com"})
    assert get(client, stranger)["items"] == []
    assert get(client, stranger, subject_id=payload["subject_id"])["items"] == []
    assert get(client, stranger, type="study_session")["items"] == []
    assert get(client, owner, type="study_session")["items"][0]["id"] == session["id"]
    for params in (
        {},
        {**WINDOW, "user_id": 1},
        {**WINDOW, "deadline_from": "2030-01-01"},
        {**WINDOW, "after_id": 1},
        {**WINDOW, "limit": 101},
        {**WINDOW, "deadline_to": WINDOW["deadline_from"]},
    ):
        r = client.get(BASE, headers=owner, params=params)
        assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
        assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("missing", ["deadline_from", "deadline_to"])
def test_required_range(client, registration, missing):
    _, headers = onboard(client, registration)
    params = {k: v for k, v in WINDOW.items() if k != missing}
    assert client.get(BASE, headers=headers, params=params).status_code == 422
