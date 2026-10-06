from dataclasses import dataclass, field

from app.models.auth_session import AuthSession


@dataclass(frozen=True)
class SessionCredentials:
    session: AuthSession
    refresh_token: str = field(repr=False)
    csrf_token: str = field(repr=False)
