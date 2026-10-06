import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_error import AuthError
from app.core.settings import Settings
from app.models.auth_session import AuthSession
from app.services.session_credentials import SessionCredentials


class SessionService:
    """Persist only hashes; serialize refresh rotation with a row lock."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._lifetime = timedelta(days=settings.refresh_token_expire_days)

    @staticmethod
    def digest(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    @staticmethod
    def parse_refresh(token: str | None) -> tuple[UUID, str]:
        try:
            session_id, secret = (token or "").split(".", 1)
            if not secret or len(secret) > 256:
                raise ValueError("Invalid secret")
            return UUID(session_id), secret
        except (ValueError, AttributeError):
            raise AuthError("INVALID_REFRESH_TOKEN") from None

    @staticmethod
    def check_csrf(cookie: str | None, header: str | None) -> None:
        if (
            not cookie
            or not header
            or len(cookie) > 256
            or len(header) > 256
            or not hmac.compare_digest(cookie.encode(), header.encode())
        ):
            raise AuthError("CSRF_VALIDATION_FAILED")

    def validate_csrf(
        self, session: AuthSession, cookie: str | None, header: str | None
    ) -> None:
        self.check_csrf(cookie, header)
        if not hmac.compare_digest(session.csrf_token_hash, self.digest(cookie or "")):
            raise AuthError("CSRF_VALIDATION_FAILED")

    def _rotate(self, session: AuthSession) -> SessionCredentials:
        secret, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        session.refresh_token_hash = self.digest(secret)
        session.csrf_token_hash = self.digest(csrf)
        session.last_used_at = datetime.now(timezone.utc)
        return SessionCredentials(session, f"{session.id}.{secret}", csrf)

    def create(self, user_id: int) -> SessionCredentials:
        now = datetime.now(timezone.utc)
        session = AuthSession(
            id=uuid4(), user_id=user_id, created_at=now, expires_at=now + self._lifetime
        )
        result = self._rotate(session)
        self._db.add(session)
        return result

    def _locked(self, session_id: UUID) -> AuthSession | None:
        return self._db.scalar(
            select(AuthSession).where(AuthSession.id == session_id).with_for_update()
        )

    def refresh(
        self, token: str | None, csrf_cookie: str | None, csrf_header: str | None
    ) -> SessionCredentials:
        session_id, secret = self.parse_refresh(token)
        session = self._locked(session_id)
        if session is None or session.expires_at <= datetime.now(timezone.utc):
            raise AuthError("INVALID_REFRESH_TOKEN")
        if session.revoked_at is not None:
            raise AuthError("SESSION_REVOKED")
        self.validate_csrf(session, csrf_cookie, csrf_header)
        if not hmac.compare_digest(session.refresh_token_hash, self.digest(secret)):
            session.revoked_at = datetime.now(timezone.utc)
            self._db.commit()  # Revocation must survive the error response.
            raise AuthError("INVALID_REFRESH_TOKEN")
        result = self._rotate(session)
        self._db.commit()
        return result

    def logout(
        self, token: str | None, csrf_cookie: str | None, csrf_header: str | None
    ) -> None:
        if token is None:  # A second logout after cookie removal is a no-op.
            return
        session_id, secret = self.parse_refresh(token)
        session = self._locked(session_id)
        if session is None:
            self.check_csrf(csrf_cookie, csrf_header)
            return
        self.validate_csrf(session, csrf_cookie, csrf_header)
        if not hmac.compare_digest(session.refresh_token_hash, self.digest(secret)):
            session.revoked_at = datetime.now(timezone.utc)
            self._db.commit()
            raise AuthError("INVALID_REFRESH_TOKEN")
        if session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
        self._db.commit()
