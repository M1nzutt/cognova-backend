from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.auth_cookies import clear_auth_cookies, set_auth_cookies
from app.api.auth_dependencies import (
    check_origin,
    get_auth_service,
    get_claims,
    get_current_user,
    limit_auth,
)
from app.models.user import User
from app.schemas.access_claims import AccessClaims
from app.schemas.auth_response import AuthResponse
from app.schemas.error_response import ErrorResponse
from app.schemas.login_request import LoginRequest
from app.schemas.refresh_response import RefreshResponse
from app.schemas.register_request import RegisterRequest
from app.schemas.session_response import SessionResponse
from app.schemas.user_response import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={
        code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429)
    },
)
Auth = Annotated[AuthService, Depends(get_auth_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Claims = Annotated[AccessClaims, Depends(get_claims)]
limited = [Depends(check_origin), Depends(limit_auth)]


@router.post(
    "/register", status_code=201, response_model=AuthResponse, dependencies=limited
)
def register(
    data: RegisterRequest, request: Request, response: Response, service: Auth
) -> AuthResponse:
    user, credentials = service.register(data)
    set_auth_cookies(response, credentials, request.app.state.settings)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=request.app.state.tokens.create(user.id, credentials.session.id),
    )


@router.post("/login", response_model=AuthResponse, dependencies=limited)
def login(
    data: LoginRequest, request: Request, response: Response, service: Auth
) -> AuthResponse:
    request.app.state.rate_limiter.check("auth-email", data.email)
    user, credentials = service.login(data)
    set_auth_cookies(response, credentials, request.app.state.settings)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=request.app.state.tokens.create(user.id, credentials.session.id),
    )


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@router.post("/refresh", response_model=RefreshResponse, dependencies=limited)
def refresh(request: Request, response: Response, service: Auth) -> RefreshResponse:
    credentials = service.sessions.refresh(
        request.cookies.get("cognova_refresh"),
        request.cookies.get("cognova_csrf"),
        request.headers.get("x-csrf-token"),
    )
    set_auth_cookies(response, credentials, request.app.state.settings)
    return RefreshResponse(
        access_token=request.app.state.tokens.create(
            credentials.session.user_id,
            credentials.session.id,
        )
    )


@router.post("/logout", status_code=204, dependencies=[Depends(check_origin)])
def logout(request: Request, service: Auth) -> Response:
    service.sessions.logout(
        request.cookies.get("cognova_refresh"),
        request.cookies.get("cognova_csrf"),
        request.headers.get("x-csrf-token"),
    )
    response = Response(status_code=204)
    clear_auth_cookies(response, request.app.state.settings)
    return response


@router.get("/sessions", response_model=list[SessionResponse])
def sessions(user: CurrentUser, claims: Claims, service: Auth) -> list[SessionResponse]:
    return service.active_sessions(user.id, claims.sid)


@router.delete("/sessions/{session_id}", status_code=204)
def revoke(
    session_id: UUID, request: Request, user: CurrentUser, service: Auth
) -> Response:
    service.revoke(user.id, session_id)
    response = Response(status_code=204)
    cookie_session_id = request.cookies.get("cognova_refresh", "").split(".", 1)[0]
    if cookie_session_id == str(session_id):
        clear_auth_cookies(response, request.app.state.settings)
    return response
