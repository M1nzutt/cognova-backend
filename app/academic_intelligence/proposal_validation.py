"""Reject unsafe model proposals before any database mutation."""

from app.academic_intelligence.academic_context import AcademicContext
from app.academic_intelligence.decision_route import DecisionRoute
from app.academic_intelligence.gemini_schemas import PlanProposal
from app.core.domain_error import DomainError
from app.schemas.study_challenge_write import StudyChallengeWrite
from app.schemas.study_plan_write import StudyPlanWrite


def validate_proposal(
    proposal: PlanProposal, context: AcademicContext
) -> tuple[StudyPlanWrite, list[StudyChallengeWrite]]:
    try:
        data = StudyPlanWrite(
            name=proposal.name,
            objective=proposal.objective,
            start_at=proposal.start_date,
            end_at=proposal.end_date,
            subject_ids=proposal.subject_ids,
            activity_ids=proposal.activity_ids,
            study_session_ids=proposal.session_ids,
        )
        viable = DecisionRoute().evaluate(
            has_resources=bool(data.subject_ids)
            and set(data.subject_ids) <= context.subject_ids
            and set(data.activity_ids) <= context.activity_ids
            and set(data.study_session_ids) <= context.session_ids,
            valid_dates=data.end_at > data.start_at,
            enough_context=bool(context.subjects),
        )
        if viable != "propose":
            raise ValueError("Unsafe proposal")
        subjects = {row.id: row for row in context.subjects}
        activities = {row.id: row for row in context.activities}
        sessions = {row.id: row for row in context.sessions}
        challenges: list[StudyChallengeWrite] = []
        seen: set[tuple[str, int | None, int | None, int | None]] = set()
        for candidate in proposal.proposed_challenges:
            if not candidate.evidence or not candidate.measurable_condition:
                raise ValueError("Challenge needs evidence and a condition")
            if candidate.target_type == "custom":
                raise ValueError("AI custom targets are not verifiable")
            if (
                candidate.start_at is not None
                and not data.start_at <= candidate.start_at <= data.end_at
            ) or (
                candidate.deadline is not None
                and not data.start_at <= candidate.deadline <= data.end_at
            ):
                raise ValueError("Challenge dates outside the plan")
            subject_id = candidate.subject_id
            activity_id = candidate.activity_id
            session_id = candidate.session_id
            if subject_id is None or subject_id not in data.subject_ids:
                raise ValueError("Challenge subject is not in plan")
            if activity_id is not None and (
                activity_id not in data.activity_ids
                or activities[activity_id].subject_id != subject_id
            ):
                raise ValueError("Challenge activity is not in plan")
            if session_id is not None and (
                session_id not in data.study_session_ids
                or sessions[session_id].subject_id != subject_id
                or (
                    activity_id is not None
                    and sessions[session_id].activity_id != activity_id
                )
            ):
                raise ValueError("Challenge session is not in plan")
            if candidate.target_id is not None and candidate.target_id not in {
                subject_id,
                activity_id,
                session_id,
            }:
                raise ValueError("Challenge target is unrelated")
            expected_target = {
                "activity_completion": activity_id,
                "session_completion": session_id,
                "subject_mastery": subject_id,
            }.get(candidate.target_type)
            if (
                candidate.target_id is not None
                and expected_target is not None
                and candidate.target_id != expected_target
            ):
                raise ValueError("Challenge target type and ID disagree")
            key = (candidate.target_type, subject_id, activity_id, session_id)
            if key in seen:
                raise ValueError("Duplicate challenge")
            seen.add(key)
            if subject_id not in subjects:
                raise ValueError("Unknown subject")
            linked_evidence = {
                f"subject:{subject_id}",
                f"activity:{activity_id}",
                f"session:{session_id}",
            }
            if any(
                token not in context.evidence_catalog for token in candidate.evidence
            ):
                raise ValueError("Invented challenge evidence")
            if not any(token in linked_evidence for token in candidate.evidence):
                raise ValueError("Challenge evidence is unrelated")
            if not (
                any(row.subject_id == subject_id for row in context.activities)
                or any(row.subject_id == subject_id for row in context.sessions)
            ):
                raise ValueError("Challenge lacks contextual records")
            challenges.append(
                StudyChallengeWrite(
                    subject_id=subject_id,
                    activity_id=activity_id,
                    study_session_id=session_id,
                    title=candidate.title,
                    description=candidate.objective,
                    target_type=candidate.target_type,
                    target_value=candidate.target_value,
                    start_at=candidate.start_at,
                    deadline=candidate.deadline,
                    generation_criteria={
                        "explanation": candidate.explanation,
                        "evidence": [
                            context.evidence_catalog[token]
                            for token in candidate.evidence
                        ],
                        "measurable_condition": candidate.measurable_condition,
                    },
                )
            )
        return data, challenges
    except (KeyError, ValueError):
        raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE") from None
