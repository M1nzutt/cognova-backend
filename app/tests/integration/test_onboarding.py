from typing import Annotated

import pytest
from fastapi import Depends

from app.api.onboarding_dependencies import get_onboarded_user
from app.models.user import User
from app.tests.questionnaire_samples import questionnaire_payload


def authenticate(client, registration):
    response = client.post("/api/v1/auth/register", json=registration)
    assert response.status_code == 201
    return response.json(), {
        "Authorization": "Bearer " + response.json()["access_token"]
    }


@pytest.mark.parametrize("questionnaire_first", [False, True])
def test_onboarding_requires_both_components_and_restore_keeps_status(
    client, registration, questionnaire_first
):
    body, headers = authenticate(client, registration)
    assert body["user"]["onboarding"] == {
        "status": "incomplete",
        "academic_profile_complete": False,
        "questionnaire_complete": False,
        "next_step": "academic_profile",
    }
    assert body["user"]["legacy_academic_goal"] is None
    refreshed = client.post(
        "/api/v1/auth/refresh", headers={"X-CSRF-Token": client.cookies["cognova_csrf"]}
    )
    headers = {"Authorization": "Bearer " + refreshed.json()["access_token"]}
    assert (
        client.get("/api/v1/auth/me", headers=headers).json()["onboarding"]["status"]
        == "incomplete"
    )
    actions = [
        lambda: client.put(
            "/api/v1/onboarding/academic-profile",
            headers=headers,
            json={"degree_program": "  Software  ", "semester": 2},
        ),
        lambda: client.post(
            "/api/v1/questionnaire", headers=headers, json=questionnaire_payload()
        ),
    ]
    if questionnaire_first:
        actions.reverse()
    assert actions[0]().status_code in (200, 201)
    assert (
        client.get("/api/v1/auth/me", headers=headers).json()["onboarding"]["status"]
        == "incomplete"
    )
    assert actions[1]().status_code in (200, 201)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["degree_program"] == "Software" and me["semester"] == 2
    assert me["onboarding"] == {
        "status": "complete",
        "academic_profile_complete": True,
        "questionnaire_complete": True,
        "next_step": "complete",
    }
    assert "academic_goal" not in me
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": client.cookies["cognova_csrf"]},
        ).status_code
        == 204
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"degree_program": " "},
        {"degree_program": None},
        {"semester": 0},
        {"semester": True},
        {"semester": "2"},
        {"semester": 1.2},
        {"semester": 2147483648},
        {"user_id": 999},
    ],
)
def test_academic_profile_rejects_invalid_input_and_ownership_injection(
    client, registration, changes
):
    _, headers = authenticate(client, registration)
    response = client.put(
        "/api/v1/onboarding/academic-profile",
        headers=headers,
        json={"degree_program": "Software", "semester": 2, **changes},
    )
    assert response.status_code == 422
    assert (
        client.get("/api/v1/auth/me", headers=headers).json()["degree_program"] is None
    )


def test_profile_ownership_and_future_academic_guard(client, registration):
    _, a = authenticate(client, registration)
    _, b = authenticate(client, {**registration, "email": "other@example.com"})

    @client.app.get("/test-academic-guard")
    def guarded(user: Annotated[User, Depends(get_onboarded_user)]):
        return {"id": user.id}

    assert client.get("/test-academic-guard", headers=a).status_code == 403
    profile = {"degree_program": "Software", "semester": 2}
    assert (
        client.put(
            "/api/v1/onboarding/academic-profile", headers=a, json=profile
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/onboarding/academic-profile", headers=a, json=profile
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=b).json()["degree_program"] is None
    client.post("/api/v1/questionnaire", headers=a, json=questionnaire_payload())
    assert client.get("/test-academic-guard", headers=a).status_code == 200
    assert client.get("/test-academic-guard", headers=b).status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/questionnaire"),
        ("get", "/questionnaire/catalog"),
        ("get", "/questionnaire/history"),
        ("post", "/questionnaire"),
        ("put", "/questionnaire"),
        ("put", "/onboarding/academic-profile"),
    ],
)
def test_onboarding_routes_require_auth(client, method, path):
    assert client.request(method, "/api/v1" + path).status_code == 401
