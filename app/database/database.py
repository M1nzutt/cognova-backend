from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import Settings


class Database:
    """Own the connection pool and provide isolated units of work."""

    def __init__(self, settings: Settings) -> None:
        self._engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={"connect_timeout": 5},
        )
        self._session_factory = sessionmaker(
            bind=self._engine, autoflush=False, expire_on_commit=False
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Close on every exit; services explicitly commit successful writes."""
        with self._session_factory() as session:
            try:
                yield session
            except Exception:
                session.rollback()
                raise

    def dispose(self) -> None:
        self._engine.dispose()
