from datetime import datetime, timezone

from fastapi import Response

from app.core.settings import Settings
from app.services.session_credentials import SessionCredentials

REFRESH_PATH = "/api/v1/auth"
CSRF_PATH = "/"


def set_auth_cookies(
    response: Response, credentials: SessionCredentials, settings: Settings
) -> None:
    max_age = max(
        0,
        int(
            (
                credentials.session.expires_at - datetime.now(timezone.utc)
            ).total_seconds()
        ),
    )
    for name, value, http_only, path in (
        ("cognova_refresh", credentials.refresh_token, True, REFRESH_PATH),
        ("cognova_csrf", credentials.csrf_token, False, CSRF_PATH),
    ):
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            path=path,
            secure=settings.cookie_secure,
            httponly=http_only,
            samesite=settings.cookie_samesite,
        )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name, http_only, path in (
        ("cognova_refresh", True, REFRESH_PATH),
        ("cognova_csrf", False, CSRF_PATH),
    ):
        response.delete_cookie(
            name,
            path=path,
            secure=settings.cookie_secure,
            httponly=http_only,
            samesite=settings.cookie_samesite,
        )
