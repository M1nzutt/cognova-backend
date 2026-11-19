from typing import Literal

from pydantic import BaseModel, ConfigDict


class BehaviorEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: int
    planned_minutes: int
    actual_seconds: str
    result: Literal["completed", "partial"]
    summary: str


class RelatedResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["subject", "activity", "session"]
    id: int
    label: str
    href: str


class BehaviorObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conclusion: str
    observation: str
    interpretation: str
    uncertainty: str
    suggestion: str
    interpretation_source: Literal["gemini", "deterministic", "fallback"]
    evidence: list[BehaviorEvidence]
    question: str
    confidence_basis: str
    related_resources: list[RelatedResource]


class BehaviorAnalysisResponse(BaseModel):
    completed_session_count: int
    partial_session_count: int
    cancelled_session_count: int
    reviewed_session_count: int
    state: Literal["factual_summary", "insufficient_data"]
    insufficient_data_guidance: str
    observations: list[BehaviorObservation]
