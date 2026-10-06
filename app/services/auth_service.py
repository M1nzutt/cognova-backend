from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth_error import AuthError
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.access_claims import AccessClaims
from app.schemas.login_request import LoginRequest
from app.schemas.register_request import RegisterRequest
from app.schemas.session_response import SessionResponse
from app.services.password_service import PasswordService
from app.services.session_credentials import SessionCredentials
from app.services.session_service import SessionService


class AuthService:
    def __init__(
        self, db: Session, passwords: PasswordService, sessions: SessionService
    ) -> None:
        self._db, self._passwords, self.sessions = db, passwords, sessions

    def register(self, data: RegisterRequest) -> tuple[User, SessionCredentials]:
        if self._db.scalar(select(User.id).where(func.lower(User.email) == data.email)):
            raise AuthError("EMAIL_ALREADY_REGISTERED")
        user = User(
            **data.model_dump(exclude={"password"}),
            password_hash=self._passwords.hash(data.password.get_secret_value()),
        )
        try:
            self._db.add(user)
            self._db.flush()
            credentials = self.sessions.create(user.id)
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            diagnostic = getattr(exc.orig, "diag", None)
            if (
                getattr(exc.orig, "sqlstate", None) == "23505"
                and getattr(diagnostic, "constraint_name", None)
                == "uq_users_email_lower"
            ):
                raise AuthError("EMAIL_ALREADY_REGISTERED") from None
            raise
        return user, credentials

    def login(self, data: LoginRequest) -> tuple[User, SessionCredentials]:
        user = self._db.scalar(select(User).where(func.lower(User.email) == data.email))
        password = data.password.get_secret_value()
        verified = self._passwords.verify(
            password, user.password_hash if user else None
        )
        if user is None or not verified:
            raise AuthError("INVALID_CREDENTIALS")
        if self._passwords.needs_rehash(user.password_hash):
            user.password_hash = self._passwords.hash(password)
        credentials = self.sessions.create(user.id)
        self._db.commit()
        return user, credentials

    def current_user(self, claims: AccessClaims) -> User:
        session = self._db.scalar(
            select(AuthSession).where(
                AuthSession.id == claims.sid,
                AuthSession.user_id == int(claims.sub),
            )
        )
        if session is None or session.expires_at <= datetime.now(timezone.utc):
            raise AuthError("INVALID_OR_EXPIRED_TOKEN")
        if session.revoked_at is not None:
            raise AuthError("SESSION_REVOKED")
        user = self._db.get(User, session.user_id)
        if user is None:
            raise AuthError("INVALID_OR_EXPIRED_TOKEN")
        return user

    def active_sessions(self, user_id: int, current_id: UUID) -> list[SessionResponse]:
        sessions = self._db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(timezone.utc),
            )
            .order_by(AuthSession.created_at.desc(), AuthSession.id)
        ).all()
        return [
            SessionResponse(
                id=s.id,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
                current=s.id == current_id,
            )
            for s in sessions
        ]

    def revoke(self, user_id: int, session_id: UUID) -> None:
        session = self._db.scalar(
            select(AuthSession)
            .where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
            )
            .with_for_update()
        )
        if session is None:
            raise AuthError("SESSION_NOT_FOUND")
        if session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
        self._db.commit()
