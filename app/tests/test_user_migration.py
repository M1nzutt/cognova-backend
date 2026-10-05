from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_user_migration_generates_postgresql_schema():
    output = StringIO()
    config = Config(
        str(Path(__file__).resolve().parents[2] / "alembic.ini"),
        output_buffer=output,
    )
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "id SERIAL NOT NULL" in sql
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in sql
    assert "CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))" in sql
    assert "CONSTRAINT ck_users_semester_positive CHECK (semester > 0)" in sql
