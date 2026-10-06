from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from sqlalchemy import func, select

from app.core.auth_error import AuthError
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.register_request import RegisterRequest
from app.services.auth_service import AuthService
from app.services.password_service import PasswordService
from app.services.rate_limit_service import RateLimitService
from app.services.session_service import SessionService


def test_concurrent_registration_relies_on_database_uniqueness(
    database, pg_settings, registration
):
    passwords = PasswordService()
    barrier = Barrier(2, timeout=10)
    original_hash = passwords.hash

    def simultaneous_hash(password):
        result = original_hash(password)
        barrier.wait()
        return result

    def register():
        with database.session() as db:
            service = AuthService(db, passwords, SessionService(db, pg_settings))
            try:
                service.register(RegisterRequest(**registration))
                return "created"
            except AuthError as exc:
                return exc.code

    with patch.object(passwords, "hash", side_effect=simultaneous_hash):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: register(), range(2)))
    assert sorted(results) == ["EMAIL_ALREADY_REGISTERED", "created"]
    with database.session() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 1


def test_concurrent_refresh_has_one_winner(client, database, pg_settings, registration):
    assert client.post("/api/v1/auth/register", json=registration).status_code == 201
    token, csrf = client.cookies["cognova_refresh"], client.cookies["cognova_csrf"]
    barrier = Barrier(2, timeout=10)

    def rotate():
        with database.session() as db:
            barrier.wait()
            try:
                result = SessionService(db, pg_settings).refresh(token, csrf, csrf)
                return "rotated", result.refresh_token
            except AuthError as exc:
                return exc.code, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: rotate(), range(2)))
    assert sorted(r[0] for r in results) == ["CSRF_VALIDATION_FAILED", "rotated"]
    with database.session() as db:
        assert db.scalar(select(AuthSession)).revoked_at is None


def test_rate_limit_is_atomic_across_instances(database, pg_settings):
    settings = pg_settings.model_copy(update={"auth_rate_limit": 3})
    barrier = Barrier(8, timeout=10)

    def consume(_):
        limiter = RateLimitService(database, settings)
        barrier.wait()
        try:
            limiter.check("auth-ip", "192.0.2.1")
            return True
        except AuthError as exc:
            assert exc.code == "TOO_MANY_REQUESTS"
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(consume, range(8))) == 3
