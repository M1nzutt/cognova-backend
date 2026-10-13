import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "n" * 30},
        {"email": "e" * 38 + "@example.com"},
        {"password": "x" * 8},
        {"password": "x" * 12},
    ],
)
def test_registration_limits_reach_real_postgresql(client, registration, changes):
    response = client.post("/api/v1/auth/register", json={**registration, **changes})
    assert response.status_code == 201
    user = response.json()["user"]
    assert user["degree_program"] is None and user["semester"] is None
    assert "password" not in user and "password_hash" not in response.text


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "n" * 31},
        {"email": "e" * 39 + "@example.com"},
        {"password": "x" * 7},
        {"password": "x" * 13},
        {"academic_goal": "old"},
        {"degree_program": "old"},
        {"semester": 2},
    ],
)
def test_public_registration_rejects_old_fields_and_out_of_range(
    client, registration, changes
):
    assert (
        client.post(
            "/api/v1/auth/register", json={**registration, **changes}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "changes",
    [{"name": "n" * 31}, {"email": "e" * 39 + "@example.com"}, {"semester": 0}],
)
def test_orm_cannot_bypass_database_registration_constraints(database, changes):
    with database.session() as db:
        db.add(
            User(
                **{
                    "name": "N",
                    "email": "n@example.com",
                    "password_hash": "test-only",
                    **changes,
                }
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
