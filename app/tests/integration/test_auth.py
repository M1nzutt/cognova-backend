from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pytest
from sqlalchemy import select

from app.models.auth_session import AuthSession
from app.models.user import User

BASE = "/api/v1/auth"


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("cognova_csrf")}


def test_register_login_me_and_hash_privacy(client, database, registration, caplog):
    result = client.post(f"{BASE}/register", json=registration)
    assert result.status_code == 201, result.text
    body = result.json()
    assert set(body) == {"user", "access_token", "token_type"}
    assert set(body["user"]) == set(registration) - {"password"} | {"id"}
    assert body["token_type"] == "bearer"
    with database.session() as db:
        user = db.get(User, body["user"]["id"])
        assert user.password_hash.startswith("$argon2id$")
        session = db.scalar(select(AuthSession))
        assert (
            client.cookies["cognova_refresh"].split(".", 1)[1]
            != session.refresh_token_hash
        )
        assert client.cookies["cognova_csrf"] != session.csrf_token_hash
    cookies = result.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert "HttpOnly" in cookies[0] and "HttpOnly" not in cookies[1]
    assert all("Secure" in c and "SameSite=lax" in c for c in cookies)
    assert "Path=/api/v1/auth" in cookies[0]
    assert "Path=/;" in cookies[1]
    me = client.get(f"{BASE}/me", headers=bearer(body["access_token"]))
    assert me.json() == body["user"]
    login = client.post(
        f"{BASE}/login",
        json={
            "email": "SARA@EXAMPLE.COM",
            "password": registration["password"],
        },
    )
    assert login.status_code == 200
    assert login.json()["user"] == body["user"]
    assert registration["password"] not in caplog.text
    assert "password_hash" not in result.text


def test_duplicate_email_case_insensitive(client, registration):
    assert client.post(f"{BASE}/register", json=registration).status_code == 201
    result = client.post(
        f"{BASE}/register", json={**registration, "email": "SARA@EXAMPLE.COM"}
    )
    assert result.status_code == 409
    assert result.json() == {
        "error": {
            "code": "EMAIL_ALREADY_REGISTERED",
            "message": "El correo ya está registrado.",
        }
    }


@pytest.mark.parametrize(
    "change",
    [
        {"name": " "},
        {"email": "invalid"},
        {"password": "short"},
        {"semester": 0},
        {"semester": True},
        {"semester": "4"},
        {"semester": 1.5},
        {"user_id": 2},
        {"degree_program": ""},
        {"academic_goal": " "},
        {"password_hash": "injected"},
    ],
)
def test_registration_validation(client, registration, change):
    result = client.post(f"{BASE}/register", json={**registration, **change})
    assert result.status_code == 422
    assert result.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Hay datos inválidos en el formulario.",
        }
    }
    assert registration["password"] not in result.text


def test_login_does_not_disclose_which_credential_failed(client, registration):
    client.post(f"{BASE}/register", json=registration)
    results = [
        client.post(f"{BASE}/login", json={"email": email, "password": "wrong"})
        for email in (registration["email"], "absent@example.com")
    ]
    assert all(r.status_code == 401 for r in results)
    assert (
        results[0].json()
        == results[1].json()
        == {
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "Correo o contraseña incorrectos.",
            }
        }
    )


def test_refresh_rotates_both_cookies_and_logout_revokes(client, registration):
    first = client.post(f"{BASE}/register", json=registration).json()
    old_refresh, old_csrf = (
        client.cookies["cognova_refresh"],
        client.cookies["cognova_csrf"],
    )
    refreshed = client.post(f"{BASE}/refresh", headers=csrf(client))
    assert refreshed.status_code == 200
    assert set(refreshed.json()) == {"access_token", "token_type"}
    assert client.cookies["cognova_refresh"] != old_refresh
    assert client.cookies["cognova_csrf"] != old_csrf
    assert client.post(f"{BASE}/logout", headers=csrf(client)).status_code == 204
    assert not client.cookies.get("cognova_refresh")
    assert not client.cookies.get("cognova_csrf")
    for token in (first["access_token"], refreshed.json()["access_token"]):
        result = client.get(f"{BASE}/me", headers=bearer(token))
        assert result.status_code == 401
        assert result.json()["error"]["code"] == "SESSION_REVOKED"
    assert client.post(f"{BASE}/logout").status_code == 204


def test_refresh_replay_with_current_csrf_revokes_session(client, registration):
    token = client.post(f"{BASE}/register", json=registration).json()["access_token"]
    old_refresh = client.cookies["cognova_refresh"]
    assert client.post(f"{BASE}/refresh", headers=csrf(client)).status_code == 200
    current_csrf = client.cookies["cognova_csrf"]
    client.cookies.clear()
    client.cookies.set("cognova_refresh", old_refresh)
    client.cookies.set("cognova_csrf", current_csrf)
    result = client.post(f"{BASE}/refresh", headers=csrf(client))
    assert result.status_code == 401
    assert result.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"
    assert (
        client.get(f"{BASE}/me", headers=bearer(token)).json()["error"]["code"]
        == "SESSION_REVOKED"
    )


@pytest.mark.parametrize("path", ["refresh", "logout"])
def test_csrf_required_and_bound_to_session(client, registration, path):
    client.post(f"{BASE}/register", json=registration)
    assert client.post(f"{BASE}/{path}").status_code == 403
    assert (
        client.post(f"{BASE}/{path}", headers={"X-CSRF-Token": "wrong"}).status_code
        == 403
    )
    client.cookies.set("cognova_csrf", "forged", domain="testserver.local", path="/")
    assert (
        client.post(f"{BASE}/{path}", headers={"X-CSRF-Token": "forged"}).status_code
        == 403
    )


def test_sessions_ownership_and_current_revocation(client, registration):
    first = client.post(f"{BASE}/register", json=registration).json()
    second = client.post(
        f"{BASE}/register", json={**registration, "email": "other@example.com"}
    ).json()
    a = client.get(f"{BASE}/sessions", headers=bearer(first["access_token"])).json()
    b = client.get(f"{BASE}/sessions", headers=bearer(second["access_token"])).json()
    assert len(a) == len(b) == 1 and a[0]["current"] and b[0]["current"]
    assert set(a[0]) == {"id", "created_at", "expires_at", "last_used_at", "current"}
    assert a[0]["id"] != b[0]["id"]
    assert (
        client.delete(
            f"{BASE}/sessions/{b[0]['id']}", headers=bearer(first["access_token"])
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"{BASE}/me?user_id={second['user']['id']}",
            headers=bearer(first["access_token"]),
        ).json()
        == first["user"]
    )
    assert (
        client.delete(
            f"{BASE}/sessions/{b[0]['id']}", headers=bearer(second["access_token"])
        ).status_code
        == 204
    )
    assert not client.cookies.get("cognova_refresh")
    assert (
        client.get(f"{BASE}/me", headers=bearer(second["access_token"])).status_code
        == 401
    )
    assert (
        client.get(f"{BASE}/me", headers=bearer(first["access_token"])).status_code
        == 200
    )


@pytest.mark.parametrize(
    "mode", ["missing", "malformed", "expired", "wrong-key", "sid", "subject"]
)
def test_rejects_invalid_access(client, pg_settings, registration, mode):
    token = client.post(f"{BASE}/register", json=registration).json()["access_token"]
    key = pg_settings.jwt_secret.get_secret_value()
    claims = jwt.decode(token, key, algorithms=["HS256"])
    if mode == "expired":
        claims["iat"], claims["exp"] = 1, 2
    if mode == "sid":
        claims["sid"] = str(uuid4())
    if mode == "subject":
        claims["sub"] = "99999"
    token = jwt.encode(claims, "x" * 48 if mode == "wrong-key" else key, "HS256")
    headers = (
        {} if mode == "missing" else bearer("invalid" if mode == "malformed" else token)
    )
    assert client.get(f"{BASE}/me", headers=headers).status_code == 401


def test_expired_persistent_session_rejects_access_and_refresh(
    client, database, registration
):
    token = client.post(f"{BASE}/register", json=registration).json()["access_token"]
    sid = UUID(client.cookies["cognova_refresh"].split(".")[0])
    with database.session() as db:
        db.get(AuthSession, sid).expires_at = datetime.now(timezone.utc) - timedelta(
            days=1
        )
        db.commit()
    assert client.get(f"{BASE}/me", headers=bearer(token)).status_code == 401
    assert client.post(f"{BASE}/refresh", headers=csrf(client)).status_code == 401
