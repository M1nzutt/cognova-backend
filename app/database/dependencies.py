from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped session from the application's database."""
    with request.app.state.database.session() as session:
        yield session
