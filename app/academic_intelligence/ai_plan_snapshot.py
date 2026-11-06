"""Versioned, user-visible AI proposal; no provider payload or private reasoning."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.academic_intelligence.gemini_schemas import PlanProposal


class SnapshotPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    objective: str
    start_date: datetime
    end_date: datetime
    subject_ids: list[int]
    activity_ids: list[int]
    session_ids: list[int]


class SnapshotChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    objective: str
    explanation: str
    evidence: list[str]
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
    measurable_condition: str
    start_date: datetime | None = None
    end_date: datetime | None = None


class AiPlanProposalSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    model: str
    generated_at: datetime
    explanation: str = Field(min_length=1, max_length=2000)
    reasoning_summary: str = Field(min_length=1, max_length=2000)
    plan: SnapshotPlan
    proposed_challenges: list[SnapshotChallenge]

    @classmethod
    def from_proposal(
        cls, proposal: PlanProposal, *, model: str, generated_at: datetime
    ) -> "AiPlanProposalSnapshot":
        return cls(
            model=model,
            generated_at=generated_at,
            explanation=proposal.explanation,
            reasoning_summary=proposal.reasoning_summary,
            plan=SnapshotPlan(
                name=proposal.name,
                objective=proposal.objective,
                start_date=proposal.start_date,
                end_date=proposal.end_date,
                subject_ids=proposal.subject_ids,
                activity_ids=proposal.activity_ids,
                session_ids=proposal.session_ids,
            ),
            proposed_challenges=[
                SnapshotChallenge(
                    title=item.title,
                    objective=item.objective,
                    explanation=item.explanation,
                    evidence=item.evidence,
                    target_type=item.target_type,
                    target_id=item.target_id,
                    subject_id=item.subject_id,
                    activity_id=item.activity_id,
                    session_id=item.session_id,
                    target_value=item.target_value,
                    measurable_condition=item.measurable_condition,
                    start_date=item.start_at,
                    end_date=item.deadline,
                )
                for item in proposal.proposed_challenges
            ],
        )

    def as_storage(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
