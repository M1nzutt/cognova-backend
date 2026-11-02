from pydantic import ConfigDict

from app.schemas.study_session_interval_response import StudySessionIntervalResponse
from app.schemas.study_session_summary import StudySessionSummary


class StudySessionDetail(StudySessionSummary):
    model_config = ConfigDict(from_attributes=True)

    other_text: str | None
    intervals: list[StudySessionIntervalResponse]
