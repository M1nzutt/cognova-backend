from sqlalchemy import text

from app.database.database import Database


class ReadinessService:
    """Check connectivity and schema before accepting production traffic."""

    expected_revision = "0002_auth_sessions"

    def __init__(self, database: Database) -> None:
        self._database = database

    def check(self) -> bool:
        with self._database.session() as session:
            session.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            connected = session.scalar(text("SELECT 1")) == 1
            revisions = session.scalars(
                text("SELECT version_num FROM alembic_version")
            ).all()
            return connected and revisions == [self.expected_revision]
