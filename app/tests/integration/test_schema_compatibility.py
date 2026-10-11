from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.database.base import Base


def test_database_release_matches_backend_orm(pg_settings):
    engine = create_engine(
        pg_settings.database_url.get_secret_value(), hide_parameters=True
    )
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={"compare_type": True, "compare_server_default": True},
            )
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()
