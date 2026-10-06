import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert

from app.core.auth_error import AuthError
from app.core.settings import Settings
from app.database.database import Database
from app.models.rate_limit_bucket import RateLimitBucket


class RateLimitService:
    """Atomic, shared PostgreSQL counters; failed requests still consume quota."""

    def __init__(self, database: Database, settings: Settings) -> None:
        self._database = database
        self._key = settings.jwt_secret.get_secret_value().encode()
        self._limit = settings.auth_rate_limit
        self._window = settings.auth_rate_window_seconds

    def check(self, category: str, identity: str) -> None:
        digest = hmac.new(
            self._key, f"{category}:{identity}".encode(), hashlib.sha256
        ).hexdigest()
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=self._window)
        bucket = RateLimitBucket
        expired = bucket.expires_at <= now
        statement = insert(bucket).values(key_hash=digest, hits=1, expires_at=expiry)
        statement = statement.on_conflict_do_update(
            index_elements=[bucket.key_hash],
            set_={
                "hits": case((expired, 1), else_=bucket.hits + 1),
                "expires_at": case((expired, expiry), else_=bucket.expires_at),
            },
        ).returning(bucket.hits)
        with self._database.session() as db:
            db.execute(
                delete(bucket).where(bucket.expires_at < now - timedelta(days=1))
            )
            hits = db.scalar(statement)
            db.commit()
        if hits is not None and hits > self._limit:
            raise AuthError("TOO_MANY_REQUESTS")
