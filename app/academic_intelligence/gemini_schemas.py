from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProposedChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    objective: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=1000)
    evidence: list[str] = Field(min_length=1, max_length=5)
    target_type: Literal[
        "study_minutes",
        "activity_completion",
        "session_completion",
        "subject_mastery",
        "custom",
    ]
    target_id: int | None = None
    subject_id: int | None = None
    activity_id: int | None = None
    session_id: int | None = None
    target_value: dict[str, Any]
    measurable_condition: str = Field(min_length=1, max_length=300)
    start_at: datetime | None = None
    deadline: datetime | None = None


class PlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    objective: str = Field(min_length=1, max_length=2000)
    start_date: datetime
    end_date: datetime
    explanation: str = Field(min_length=1, max_length=2000)
    subject_ids: list[int] = Field(max_length=100)
    activity_ids: list[int] = Field(max_length=200)
    session_ids: list[int] = Field(max_length=200)
    proposed_challenges: list[ProposedChallenge] = Field(max_length=30)
    reasoning_summary: str = Field(min_length=1, max_length=2000)


class BehaviorObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: str = Field(min_length=1, max_length=1000)
    evidence: list[str] = Field(min_length=1, max_length=5)
    question: str = Field(min_length=1, max_length=500)
    confidence_basis: str = Field(min_length=1, max_length=500)
    related_subject_ids: list[int] = Field(max_length=20)
    related_activity_ids: list[int] = Field(max_length=20)
    related_session_ids: list[int] = Field(max_length=20)


class BehaviorProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[BehaviorObservation] = Field(max_length=5)
