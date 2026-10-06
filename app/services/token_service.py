from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from pydantic import ValidationError

from app.core.auth_error import AuthError
from app.core.settings import Settings
from app.schemas.access_claims import AccessClaims


class TokenService:
    """Issue and validate signed, expiring access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._lifetime = timedelta(minutes=settings.access_token_expire_minutes)

    def create(self, user_id: int, session_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "jti": str(uuid4()),
                "type": "access",
                "iat": now,
                "exp": now + self._lifetime,
            },
            self._secret,
            algorithm=self._algorithm,
        )

    def verify(self, token: str) -> AccessClaims:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "sid", "type", "iat", "exp"]},
            )
            validated = AccessClaims.model_validate(claims)
            if validated.exp <= validated.iat:
                raise ValueError("Invalid lifetime")
            return validated
        except (
            jwt.InvalidTokenError,
            ValidationError,
            ValueError,
            TypeError,
            OverflowError,
        ):
            raise AuthError("INVALID_OR_EXPIRED_TOKEN") from None
