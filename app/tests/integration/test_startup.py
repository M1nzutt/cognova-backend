from sqlalchemy import text

from scripts.start import migrate


def test_startup_migration_can_run_again_without_destroying_users(
    client, pg_settings, database, registration
):
    assert client.post("/api/v1/auth/register", json=registration).status_code == 201
    migrate(pg_settings)
    migrate(pg_settings)
    with database.session() as session:
        assert session.scalar(text("SELECT count(*) FROM users")) == 1
        assert session.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
    assert client.get("/api/v1/ready").status_code == 200
