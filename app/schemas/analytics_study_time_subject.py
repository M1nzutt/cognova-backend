from pydantic import BaseModel


class AnalyticsStudyTimeSubject(BaseModel):
    subject_id: int
    name: str
    seconds: str
    minutes: str
    sessions_count: int


__all__ = ["AnalyticsStudyTimeSubject"]
