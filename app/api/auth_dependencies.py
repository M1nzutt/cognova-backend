from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth_error import AuthError
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.access_claims import AccessClaims
from app.services.auth_service import AuthService
from app.services.session_service import SessionService

bearer = HTTPBearer(auto_error=False)


def get_auth_service(
    request: Request, db: Annotated[Session, Depends(get_session)]
) -> AuthService:
    return AuthService(
        db, request.app.state.passwords, SessionService(db, request.app.state.settings)
    )


def get_claims(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer),
    ],
) -> AccessClaims:
    if credentials is None:
        raise AuthError("INVALID_OR_EXPIRED_TOKEN")
    return request.app.state.tokens.verify(credentials.credentials)


def get_current_user(
    service: Annotated[AuthService, Depends(get_auth_service)],
    claims: Annotated[AccessClaims, Depends(get_claims)],
) -> User:
    return service.current_user(claims)


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.cors_allowed_origins:
        raise AuthError("FORBIDDEN")


def limit_auth(request: Request) -> None:
    # Do not trust arbitrary forwarded headers for IP attribution.
    host = request.client.host if request.client else "unknown"
    request.app.state.rate_limiter.check("auth-ip", host)
