from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.questionnaire_response import QuestionnaireResponseRecord
from app.tests.integration.test_onboarding import authenticate
from app.tests.questionnaire_samples import questionnaire_payload

BASE = "/api/v1/questionnaire"


def test_initial_current_update_and_paginated_history(client, registration, database):
    _, headers = authenticate(client, registration)
    assert client.get(BASE, headers=headers).status_code == 404
    assert client.get(BASE + "/history", headers=headers).json() == {
        "items": [],
        "next_before_revision": None,
    }
    first = client.post(BASE, headers=headers, json=questionnaire_payload())
    assert first.status_code == 201
    initial = first.json()
    assert initial["revision"] == 1
    assert set(initial) == {
        "revision",
        "questionnaire_version",
        "answers",
        "recorded_at",
    }
    assert (
        client.post(BASE, headers=headers, json=questionnaire_payload()).status_code
        == 409
    )
    for revision in (1, 2):
        payload = questionnaire_payload()
        payload["answers"]["q1"] = {
            "choices": ["other"],
            "other_text": "  nueva: meta  ",
        }
        result = client.put(
            BASE, headers=headers, json={**payload, "expected_revision": revision}
        )
        assert result.status_code == 200
        assert result.json()["revision"] == revision + 1
        assert result.json()["answers"]["q1"]["other_text"] == "nueva: meta"
    assert (
        client.put(
            BASE,
            headers=headers,
            json={**questionnaire_payload(), "expected_revision": 1},
        ).status_code
        == 409
    )
    assert client.get(BASE, headers=headers).json()["revision"] == 3
    page = client.get(BASE + "/history?limit=2", headers=headers).json()
    assert [item["revision"] for item in page["items"]] == [3, 2]
    assert page["next_before_revision"] == 2
    last = client.get(
        BASE + "/history?before_revision=2&limit=2", headers=headers
    ).json()
    assert last == {"items": [initial], "next_before_revision": None}
    with database.session() as db:
        with pytest.raises(IntegrityError):
            db.execute(text("UPDATE questionnaire_responses SET revision=99"))
            db.commit()
    with database.session() as db:
        assert len(db.scalars(select(QuestionnaireResponseRecord)).all()) == 3


def test_questionnaire_ownership_catalog_and_incomplete_update(client, registration):
    _, a = authenticate(client, registration)
    _, b = authenticate(client, {**registration, "email": "b@example.com"})
    assert (
        client.put(
            BASE, headers=a, json={**questionnaire_payload(), "expected_revision": 1}
        ).status_code
        == 404
    )
    first = client.post(BASE, headers=a, json=questionnaire_payload()).json()
    assert client.get(BASE, headers=b).status_code == 404
    assert client.get(BASE + "/history", headers=b).json()["items"] == []
    assert (
        client.post(
            BASE, headers=b, json={**questionnaire_payload(), "user_id": 1}
        ).status_code
        == 422
    )
    assert client.get(BASE + "?user_id=1", headers=b).status_code == 404
    assert client.get(BASE, headers=a).json() == first
    catalog = client.get(BASE + "/catalog", headers=b)
    assert catalog.status_code == 200 and catalog.headers["cache-control"] == "no-store"
    assert len(catalog.json()["questions"]) == 10


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "before_revision=0", "limit=abc"]
)
def test_history_validates_cursor(client, registration, query):
    _, headers = authenticate(client, registration)
    assert client.get(BASE + "/history?" + query, headers=headers).status_code == 422


@pytest.mark.parametrize("update", [False, True])
def test_concurrent_questionnaire_writes_have_one_winner(client, registration, update):
    _, headers = authenticate(client, registration)
    if update:
        assert (
            client.post(BASE, headers=headers, json=questionnaire_payload()).status_code
            == 201
        )

    def write():
        # Independent request clients; the application's lifespan is already running.
        worker = TestClient(client.app, base_url="https://testserver")
        try:
            payload = questionnaire_payload()
            if update:
                payload["expected_revision"] = 1
            return worker.request(
                "PUT" if update else "POST", BASE, headers=headers, json=payload
            ).status_code
        finally:
            worker.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: write(), range(2)))
    assert sorted(statuses) == [200 if update else 201, 409]
    assert client.get(BASE, headers=headers).json()["revision"] == (2 if update else 1)
