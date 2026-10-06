import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models.rate_limit_bucket import RateLimitBucket
from app.services.rate_limit_service import RateLimitService


@pytest.mark.parametrize("path", ["register", "login", "refresh"])
def test_http_rate_limit_and_expiry(pg_settings, database, registration, path):
    settings = pg_settings.model_copy(update={"auth_rate_limit": 2})
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        payload = (
            registration
            if path == "register"
            else {
                "email": registration["email"],
                "password": "wrong-password",
            }
        )
        for _ in range(2):
            assert client.post(f"/api/v1/auth/{path}", json=payload).status_code != 429
        result = client.post(f"/api/v1/auth/{path}", json=payload)
        assert result.status_code == 429
        assert result.json()["error"]["code"] == "TOO_MANY_REQUESTS"
        assert int(result.headers["Retry-After"]) > 0
        with database.session() as db:
            for bucket in db.scalars(select(RateLimitBucket)):
                assert registration["email"] not in bucket.key_hash
                bucket.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        assert client.post(f"/api/v1/auth/{path}", json=payload).status_code != 429


def test_email_limit_survives_different_ip_buckets(database, pg_settings):
    limiter = RateLimitService(
        database, pg_settings.model_copy(update={"auth_rate_limit": 1})
    )
    limiter.check("auth-email", "target@example.com")
    from app.core.auth_error import AuthError

    with pytest.raises(AuthError) as caught:
        limiter.check("auth-email", "target@example.com")
    assert caught.value.code == "TOO_MANY_REQUESTS"


def test_untrusted_origin_cannot_log_in_or_rotate(client, registration):
    result = client.post(
        "/api/v1/auth/register",
        json=registration,
        headers={"Origin": "https://evil.example"},
    )
    assert result.status_code == 403
    assert not client.cookies


def test_secrets_are_not_logged_and_headers_prevent_caching(
    client, registration, caplog
):
    caplog.set_level("INFO", logger="cognova.requests")
    result = client.post("/api/v1/auth/register", json=registration)
    assert result.status_code == 201
    assert result.headers["Cache-Control"] == "no-store"
    assert result.headers["X-Content-Type-Options"] == "nosniff"
    assert result.headers["X-Request-ID"]
    events = [
        json.loads(r.message) for r in caplog.records if r.name == "cognova.requests"
    ]
    assert events[-1]["route"] == "/api/v1/auth/register"
    for secret in (
        registration["password"],
        registration["email"],
        client.cookies["cognova_refresh"],
        result.json()["access_token"],
    ):
        assert secret not in caplog.text


def test_body_limit_rejects_before_database_work(client):
    result = client.post("/api/v1/auth/login", content=b"x" * (1048576 + 1))
    assert result.status_code == 413


def test_refresh_never_authenticates_from_json(client, registration):
    client.post("/api/v1/auth/register", json=registration)
    refresh, csrf = client.cookies["cognova_refresh"], client.cookies["cognova_csrf"]
    client.cookies.clear()
    result = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
        headers={"X-CSRF-Token": csrf},
    )
    assert result.status_code == 401
