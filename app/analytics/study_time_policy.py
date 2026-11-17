from sqlalchemy import ColumnElement

from app.models.study_session import StudySession


def is_cancelled_session(status: str | None) -> bool:
    return status == "cancelled"


def included_in_study_time() -> ColumnElement[bool]:
    """Keep cancelled timer duration auditable, but out of studied-time totals."""
    return StudySession.status.is_distinct_from("cancelled")


__all__ = ["included_in_study_time", "is_cancelled_session"]
