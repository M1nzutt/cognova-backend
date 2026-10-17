"""Live demo check: creates one synthetic user; never prints credentials."""

import secrets
import sys
from urllib.parse import urlsplit

import httpx


def require(response: httpx.Response, expected: int, step: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(f"{step}: expected {expected}, got {response.status_code}")
    if "no-store" not in response.headers.get("cache-control", "").lower():
        raise RuntimeError(f"{step}: missing no-store")
    print(f"{step}: {expected}")


def check_onboarding(client: httpx.Client, headers: dict[str, str]) -> None:
    response = client.put(
        "/api/v1/onboarding/academic-profile",
        headers=headers,
        json={"degree_program": "Operational smoke", "semester": 1},
    )
    require(response, 200, "academic-profile")
    response = client.get("/api/v1/questionnaire/catalog", headers=headers)
    require(response, 200, "questionnaire catalog")
    catalog = response.json()
    answers = {
        q["id"]: {
            "choices": [next(o["id"] for o in q["options"] if o["id"] != "other")],
            "other_text": None,
        }
        for q in catalog["questions"]
    }
    if len(answers) != 10:
        raise RuntimeError("Unexpected catalog size")
    payload = {
        "questionnaire_version": catalog["questionnaire_version"],
        "answers": answers,
    }
    response = client.post("/api/v1/questionnaire", headers=headers, json=payload)
    require(response, 201, "initial questionnaire")
    initial = response.json()
    response = client.get("/api/v1/questionnaire", headers=headers)
    require(response, 200, "current questionnaire")
    if response.json() != initial or initial["revision"] != 1:
        raise RuntimeError("Initial questionnaire mismatch")
    update = {**payload, "expected_revision": 1}
    response = client.put("/api/v1/questionnaire", headers=headers, json=update)
    require(response, 200, "questionnaire update")
    if response.json()["revision"] != 2:
        raise RuntimeError("Unexpected questionnaire revision")
    require(
        client.put("/api/v1/questionnaire", headers=headers, json=update),
        409,
        "stale questionnaire revision",
    )
    response = client.get("/api/v1/questionnaire/history", headers=headers)
    require(response, 200, "questionnaire history")
    items = response.json()["items"]
    if [item["revision"] for item in items] != [2, 1] or items[1] != initial:
        raise RuntimeError("Initial perception was not preserved")
    response = client.get("/api/v1/auth/me", headers=headers)
    require(response, 200, "completed onboarding")
    if response.json()["onboarding"]["status"] != "complete":
        raise RuntimeError("Onboarding did not complete")


def main() -> None:
    origin = sys.argv[1].rstrip("/")
    parts = urlsplit(origin)
    if parts.scheme != "https" or not parts.hostname or parts.path:
        raise SystemExit("Use an HTTPS origin without a path")
    payload = {
        "name": "Demo smoke test",
        "email": f"smoke-{secrets.token_hex(12)}@example.com",
        "password": secrets.token_urlsafe(9),
    }
    with httpx.Client(base_url=origin, timeout=90, follow_redirects=False) as client:
        require(client.get("/api/v1/health"), 200, "health")
        require(client.get("/api/v1/ready"), 200, "readiness")
        require(client.get("/api/v1/auth/me"), 401, "me without session")
        schema = client.get("/openapi.json")
        if (
            schema.status_code != 200
            or "/api/v1/questionnaire/history" not in schema.json()["paths"]
        ):
            raise RuntimeError("Onboarding OpenAPI unavailable")
        print("openapi: 200")
        client.headers["Origin"] = sys.argv[2] if len(sys.argv) > 2 else origin
        response = client.post("/api/v1/auth/register", json=payload)
        require(response, 201, "register")
        if response.json()["user"]["onboarding"]["status"] != "incomplete":
            raise RuntimeError("Registration unexpectedly complete")
        first_access = response.json()["access_token"]
        user_id = response.json()["user"]["id"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        require(response, 200, "login")
        access = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        require(response, 200, "me")
        if response.json()["id"] != user_id or "password_hash" in response.json():
            raise RuntimeError("Unexpected user response")
        check_onboarding(client, headers)
        cookies = {cookie.name: cookie for cookie in client.cookies.jar}
        refresh, csrf = cookies["cognova_refresh"], cookies["cognova_csrf"]
        if (
            refresh.path != "/api/v1/auth"
            or not refresh.secure
            or not refresh.has_nonstandard_attr("HttpOnly")
            or csrf.path != "/"
            or not csrf.secure
            or csrf.has_nonstandard_attr("HttpOnly")
            or refresh.domain_specified
            or csrf.domain_specified
            or str(refresh.get_nonstandard_attr("SameSite")).lower() != "lax"
            or str(csrf.get_nonstandard_attr("SameSite")).lower() != "lax"
        ):
            raise RuntimeError("Unexpected cookie attributes")
        old_refresh = refresh.value
        require(client.post("/api/v1/auth/refresh"), 403, "csrf rejection")
        response = client.post(
            "/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf.value}
        )
        require(response, 200, "refresh")
        if client.cookies.get("cognova_refresh") == old_refresh:
            raise RuntimeError("Refresh was not rotated")
        access = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        require(client.get("/api/v1/auth/me", headers=headers), 200, "me after refresh")
        response = client.get("/api/v1/auth/sessions", headers=headers)
        require(response, 200, "sessions")
        for session in response.json():
            if not session["current"]:
                require(
                    client.delete(
                        f"/api/v1/auth/sessions/{session['id']}", headers=headers
                    ),
                    204,
                    "revoke other session",
                )
        require(
            client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {first_access}"},
            ),
            401,
            "revoked access",
        )
        require(
            client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": client.cookies.get("cognova_csrf")},
            ),
            204,
            "logout",
        )
        require(client.get("/api/v1/auth/me", headers=headers), 401, "logged out")
    print("PASS: one synthetic demo user remains; all its sessions are revoked")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Smoke failed ({type(exc).__name__}); no credentials logged")
