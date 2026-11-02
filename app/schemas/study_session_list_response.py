from pydantic import BaseModel

from app.schemas.study_session_cursor import StudySessionCursor
from app.schemas.study_session_summary import StudySessionSummary


class StudySessionListResponse(BaseModel):
    items: list[StudySessionSummary]
    next_cursor: StudySessionCursor | None
