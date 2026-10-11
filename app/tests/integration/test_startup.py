from sqlalchemy import text
from sqlalchemy.engine import make_url

from scripts.start import require_compatible_database


def test_startup_accepts_read_only_connection_without_modifying_users(
    client, pg_settings, database, registration
):
    assert client.post("/api/v1/auth/register", json=registration).status_code == 201
    url = make_url(pg_settings.database_url.get_secret_value())
    url = url.update_query_dict(
        {"options": url.query["options"] + " -cdefault_transaction_read_only=on"}
    )
    settings = type(pg_settings)(
        _env_file=None, database_url=url.render_as_string(hide_password=False)
    )
    require_compatible_database(settings)
    require_compatible_database(settings)
    with database.session() as session:
        assert session.scalar(text("SELECT count(*) FROM users")) == 1
        assert session.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
    assert client.get("/api/v1/ready").status_code == 200
