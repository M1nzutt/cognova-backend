import pytest
from pydantic import ValidationError

from app.schemas.register_request import RegisterRequest

BASE = {"name": "Sara", "email": "sara@example.com", "password": "password8"}


@pytest.mark.parametrize(
    "change",
    [
        {"name": "a" * 30},
        {"email": "a" * 38 + "@example.com"},
        {"password": "a" * 8},
        {"password": "a" * 12},
    ],
)
def test_registration_boundaries_accept(change):
    assert RegisterRequest.model_validate({**BASE, **change})


@pytest.mark.parametrize(
    "change",
    [
        {"name": "a" * 31},
        {"name": "  "},
        {"email": "a" * 39 + "@example.com"},
        {"email": "invalid"},
        {"password": "a" * 7},
        {"password": "a" * 13},
        {"degree_program": "Software"},
        {"semester": 1},
        {"academic_goal": "Goal"},
    ],
)
def test_registration_boundaries_reject(change):
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate({**BASE, **change})


def test_registration_trims_name_and_preserves_password():
    result = RegisterRequest.model_validate(
        {
            **BASE,
            "name": "  Sara  ",
            "email": "SARA@EXAMPLE.COM",
            "password": "  secret8  ",
        }
    )
    assert result.name == "Sara"
    assert result.email == "sara@example.com"
    assert result.password.get_secret_value() == "  secret8  "
    assert "secret8" not in repr(result)
