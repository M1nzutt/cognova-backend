import math
import re
from datetime import datetime, timedelta, timezone

import jwt

from app.core.auth_error import AuthError
from app.core.settings import Settings


class TokenService:
    """Issue and validate signed, expiring access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._lifetime = timedelta(minutes=settings.jwt_expire_minutes)

    def create(self, user_id: int, email: str) -> str:
        return jwt.encode(
            {
                "sub": str(user_id),
                "email": email,
                "exp": datetime.now(timezone.utc) + self._lifetime,
            },
            self._secret,
            algorithm=self._algorithm,
        )

    def verify(self, token: str) -> tuple[int, str]:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "email", "exp"]},
            )
            subject, email, expires = claims["sub"], claims["email"], claims["exp"]
            if (
                not isinstance(subject, str)
                or re.fullmatch(r"[1-9][0-9]{0,9}", subject) is None
                or int(subject) > 2147483647
                or not isinstance(email, str)
                or not email
                or type(expires) not in (int, float)
                or not math.isfinite(expires)
            ):
                raise ValueError("Invalid claims")
            return int(subject), email
        except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
            raise AuthError("INVALID_OR_EXPIRED_TOKEN") from None
