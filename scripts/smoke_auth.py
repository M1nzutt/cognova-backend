"""Live demo check: creates one synthetic user; never prints credentials."""

import secrets
import sys
from urllib.parse import urlsplit

import httpx


def require(response: httpx.Response, expected: int, step: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(f"{step}: expected {expected}, got {response.status_code}")
    print(f"{step}: {expected}")


def main() -> None:
    origin = sys.argv[1].rstrip("/")
    parts = urlsplit(origin)
    if parts.scheme != "https" or not parts.hostname or parts.path:
        raise SystemExit("Use an HTTPS origin without a path")
    payload = {
        "name": "Demo smoke test",
        "email": f"smoke-{secrets.token_hex(12)}@example.com",
        "password": secrets.token_urlsafe(32),
        "degree_program": "Software",
        "semester": 1,
        "academic_goal": "Verificar autenticación desplegada",
    }
    with httpx.Client(base_url=origin, timeout=90, follow_redirects=False) as client:
        require(client.get("/api/v1/ready"), 200, "readiness")
        client.headers["Origin"] = sys.argv[2] if len(sys.argv) > 2 else origin
        response = client.post("/api/v1/auth/register", json=payload)
        require(response, 201, "register")
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
        cookies = {cookie.name: cookie for cookie in client.cookies.jar}
        refresh, csrf = cookies["cognova_refresh"], cookies["cognova_csrf"]
        if (
            refresh.path != "/api/v1/auth"
            or not refresh.secure
            or not refresh.has_nonstandard_attr("HttpOnly")
            or csrf.path != "/"
            or not csrf.secure
            or csrf.has_nonstandard_attr("HttpOnly")
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
