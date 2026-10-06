"""Migrate before listening; never serve an unmigrated deployment."""

import logging
import os

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.core.settings import Settings


def migrate(settings: Settings) -> None:
    engine = create_engine(
        settings.database_url.get_secret_value(),
        poolclass=NullPool,
        hide_parameters=True,
        connect_args={"connect_timeout": 10},
    )
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL lock_timeout = '30s'"))
            connection.execute(text("SET LOCAL statement_timeout = '120s'"))
            # Serialize migrations when two instances start concurrently.
            connection.execute(text("SELECT pg_advisory_xact_lock(1943187001)"))
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        settings = Settings()
        port = int(os.environ.get("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid port")
        migrate(settings)
    except Exception as exc:
        # Configuration/DB exceptions can contain credentials; omit their text.
        logging.error("startup_failed exception_type=%s", type(exc).__name__)
        raise SystemExit(1) from None
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=port,
        access_log=False,
        proxy_headers=False,
        workers=1,
        timeout_keep_alive=5,
    )


if __name__ == "__main__":
    main()
