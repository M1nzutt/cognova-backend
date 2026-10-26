import pytest
from sqlalchemy import text

from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_onboarding import authenticate
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
            for table in ("activities", "activity_deadline_events", "subjects")
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


def test_calendar_authorization_and_invalid_queries(client, registration):
    assert client.get(BASE, params=WINDOW).status_code == 401
    _, incomplete = authenticate(client, registration)
    assert client.get(BASE, headers=incomplete, params=WINDOW).status_code == 403
    _, owner, payload, _ = setup_activity(
        client, {**registration, "email": "owner@example.com"}
    )
    _, stranger = onboard(client, {**registration, "email": "stranger@example.com"})
    assert get(client, stranger)["items"] == []
    assert get(client, stranger, subject_id=payload["subject_id"])["items"] == []
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
