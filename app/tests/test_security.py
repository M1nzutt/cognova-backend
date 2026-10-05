from datetime import datetime, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.core.auth_error import AuthError
from app.core.settings import Settings
from app.schemas.register_request import RegisterRequest
from app.services.password_service import PasswordService
from app.services.token_service import TokenService


def test_password_hash_is_salted_and_verified_without_truncation():
    service = PasswordService()
    password = "á " * 80
    first, second = service.hash(password), service.hash(password)
    assert first != second
    assert first.startswith("$argon2id$")
    assert password not in first
    assert service.verify(password, first)
    assert not service.verify(password[:-1], first)
    assert not service.verify(password, None)
    assert not service.verify(password, "broken-hash")
    assert not service.needs_rehash(first)


def test_tokens_include_contract_claims_and_expiration():
    settings = Settings(_env_file=None)
    service = TokenService(settings)
    now = datetime.now(timezone.utc).timestamp()
    token = service.create(7, "sara@example.com")
    claims = jwt.decode(
        token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"]
    )
    assert service.verify(token) == (7, "sara@example.com")
    assert set(claims) == {"sub", "email", "exp"}
    assert now + 3598 < claims["exp"] <= now + 3601


@pytest.mark.parametrize(
    "change", [
        {"exp": 1}, {"exp": None}, {"exp": "tomorrow"}, {"exp": float("inf")},
        {"sub": "0"}, {"sub": "-1"}, {"sub": "01"}, {"sub": "2147483648"},
        {"sub": "1 OR 1=1"}, {"sub": 1}, {"email": []}, {"email": ""},
    ],
)
def test_rejects_invalid_claims(change):
    settings = Settings(_env_file=None)
    claims = {"sub": "1", "email": "sara@example.com", "exp": 4102444800}
    claims.update(change)
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), "HS256")
    with pytest.raises(AuthError, match="La sesión expiró"):
        TokenService(settings).verify(token)


@pytest.mark.parametrize("missing", ["sub", "email", "exp"])
def test_rejects_missing_claims(missing):
    settings = Settings(_env_file=None)
    claims = {"sub": "1", "email": "sara@example.com", "exp": 4102444800}
    del claims[missing]
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), "HS256")
    with pytest.raises(AuthError):
        TokenService(settings).verify(token)


@pytest.mark.parametrize("algorithm", ["HS384", "none"])
def test_rejects_unapproved_algorithm(algorithm):
    settings = Settings(_env_file=None)
    token = jwt.encode(
        {"sub": "1", "email": "sara@example.com", "exp": 4102444800},
        None if algorithm == "none" else settings.jwt_secret.get_secret_value(),
        algorithm=algorithm,
    )
    with pytest.raises(AuthError):
        TokenService(settings).verify(token)


def test_requires_strong_secret_and_valid_configuration(monkeypatch):
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
    for overrides in (
        {"jwt_secret": "short"},
        {"jwt_secret": "x" * 32, "jwt_algorithm": "none"},
        {"jwt_secret": "x" * 32, "jwt_expire_minutes": 0},
    ):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **overrides)


def test_registration_preserves_password_and_normalizes_email():
    payload = RegisterRequest(
        name="Sara", email="SARA@EXAMPLE.COM", password=" secret12 ",
        degree_program="Software", semester=4, academic_goal="Estudiar",
    )
    assert payload.email == "sara@example.com"
    assert payload.password.get_secret_value() == " secret12 "
    assert " secret12 " not in repr(payload)
