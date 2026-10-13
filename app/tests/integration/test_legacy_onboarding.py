from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from sqlalchemy import text

from app.tests.database_tooling import database_checkout, migrate_test_schema
from app.tests.questionnaire_samples import questionnaire_payload


@pytest.mark.parametrize("pg_settings", ["0002_auth_sessions"], indirect=True)
@pytest.mark.parametrize("goal", ["Meta antigua", "", "  ñ objetivo  "])
def test_migrated_user_and_existing_session_preserve_legacy_perception(
    client, database, pg_settings, goal
):
    password = "legacy-password-longer-than12"
    hashed = PasswordHasher().hash(password)
    sid = uuid4()
    now = datetime.now(timezone.utc)
    with database.session() as db:
        user_id = db.scalar(
            text(
                "INSERT INTO users "
                "(name,email,password_hash,degree_program,semester,academic_goal) "
                "VALUES ('Legacy','legacy@example.com',:hash,'Software',3,:goal) "
                "RETURNING id"
            ),
            {"hash": hashed, "goal": goal},
        )
        db.execute(
            text(
                "INSERT INTO auth_sessions "
                "(id,user_id,refresh_token_hash,csrf_token_hash,"
                "expires_at,last_used_at) "
                "VALUES (:sid,:uid,:refresh,:csrf,:expires,:now)"
            ),
            {
                "sid": sid,
                "uid": user_id,
                "refresh": "a" * 64,
                "csrf": "b" * 64,
                "expires": now + timedelta(days=1),
                "now": now,
            },
        )
        db.commit()
    migrate_test_schema(
        database_checkout(), pg_settings.database_url.get_secret_value()
    )
    old_token = client.app.state.tokens.create(user_id, sid)
    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + old_token})
    assert me.status_code == 200
    assert me.json()["legacy_academic_goal"]["value"] == goal
    assert me.json()["onboarding"]["status"] == "incomplete"
    login = client.post(
        "/api/v1/auth/login", json={"email": "legacy@example.com", "password": password}
    )
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert (
        client.post(
            "/api/v1/questionnaire", headers=headers, json=questionnaire_payload()
        ).status_code
        == 201
    )
    completed = client.get("/api/v1/auth/me", headers=headers).json()
    assert completed["onboarding"]["status"] == "complete"
    assert completed["legacy_academic_goal"] == me.json()["legacy_academic_goal"]
    with database.session() as db:
        assert (
            db.scalar(
                text("SELECT academic_goal FROM users WHERE id=:id"), {"id": user_id}
            )
            == goal
        )
        assert db.scalar(text("SELECT count(*) FROM questionnaire_responses")) == 1


@pytest.mark.parametrize("pg_settings", ["0002_auth_sessions"], indirect=True)
def test_nonconforming_legacy_identity_can_login_without_silent_truncation(
    client, database, pg_settings
):
    name = "x" * 31
    email = "a" * 39 + "@example.com"
    password = "legacy-password-longer-than12"
    hashed = PasswordHasher(time_cost=1).hash(password)
    with database.session() as db:
        db.execute(
            text(
                "INSERT INTO users "
                "(name,email,password_hash,degree_program,semester,academic_goal) "
                "VALUES (:name,:email,:hash,'Software',3,'goal')"
            ),
            {"name": name, "email": email, "hash": hashed},
        )
        db.commit()
    migrate_test_schema(
        database_checkout(), pg_settings.database_url.get_secret_value()
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200
    assert login.json()["user"]["name"] == name
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    result = client.put(
        "/api/v1/onboarding/academic-profile",
        headers=headers,
        json={"degree_program": "Software", "semester": 4},
    )
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "LEGACY_PROFILE_REMEDIATION_REQUIRED"
    with database.session() as db:
        assert db.scalar(text("SELECT password_hash FROM users")) == hashed
