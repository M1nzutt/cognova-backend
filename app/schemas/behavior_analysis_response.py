from pydantic import BaseModel

from app.academic_intelligence.gemini_schemas import BehaviorObservation


class BehaviorAnalysisResponse(BaseModel):
    finished_session_count: int
    pattern_eligible: bool
    observations: list[BehaviorObservation]
