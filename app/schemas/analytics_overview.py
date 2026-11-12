from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total_studied_seconds: str
    total_studied_minutes: str
    finished_sessions: int
    completed_sessions: int
    partial_sessions: int
    postponed_sessions: int
    cancelled_sessions: int
    subjects_with_activity: int
    completed_activities: int
    pending_activities: int
    in_progress_activities: int
    active_plans: int
    completed_plans: int
    completed_challenges: int
    failed_challenges: int


__all__ = ["AnalyticsOverview"]
