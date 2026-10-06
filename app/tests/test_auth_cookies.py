from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from uuid import uuid4

from fastapi import Response

from app.api.auth_cookies import clear_auth_cookies, set_auth_cookies
from app.core.settings import Settings
from app.models.auth_session import AuthSession
from app.services.session_credentials import SessionCredentials


def test_cookie_paths_and_security_match_same_origin_deployment():
    settings = Settings(_env_file=None)
    response = Response()
    session = AuthSession(
        id=uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    credentials = SessionCredentials(session, "opaque-token", "csrf-token")
    set_auth_cookies(response, credentials, settings)
    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)
    assert cookies["cognova_refresh"]["path"] == "/api/v1/auth"
    assert cookies["cognova_csrf"]["path"] == "/"
    assert cookies["cognova_refresh"]["httponly"]
    assert not cookies["cognova_csrf"]["httponly"]
    assert all(
        c["secure"] and c["samesite"] == "lax" and not c["domain"]
        for c in cookies.values()
    )
    response = Response()
    clear_auth_cookies(response, settings)
    for header in response.headers.getlist("set-cookie"):
        deleted = SimpleCookie(header)
        for name, cookie in deleted.items():
            assert cookie["path"] == cookies[name]["path"]
            assert cookie["max-age"] == "0"
