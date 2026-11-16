"""Reject unsafe model proposals before any database mutation."""

import logging

from pydantic import ValidationError

from app.academic_intelligence.academic_context import AcademicContext
from app.academic_intelligence.decision_route import DecisionRoute
from app.academic_intelligence.gemini_schemas import PlanProposal
from app.core.domain_error import DomainError
from app.schemas.study_challenge_write import StudyChallengeWrite
from app.schemas.study_plan_write import StudyPlanWrite

_logger = logging.getLogger(__name__)
_SAFE_CODE = "AI_PROPOSAL_RULE_REJECTED"
_WRITE_RULES = {
    "Invalid control characters": "text_controls",
    "Resource identifiers must be unique": "unique_resource_ids",
    "end_at must be later than start_at": "plan_date_order",
    "Target value must be a small non-empty object": "target_value_size",
    "Generation criteria must be a small non-empty object": "criteria_size",
    "Value must contain only JSON-compatible data": "json_compatible_values",
    "study_minutes requires a contextual 1–1440 minute target": "study_minutes_target",
    "activity_completion requires a completed activity target": (
        "activity_completion_target"
    ),
    "session_completion requires a finished session target": (
        "session_completion_target"
    ),
    "subject_mastery requires a criterion and a 1–100 threshold": (
        "subject_mastery_target"
    ),
    "deadline must not be before start_at": "challenge_date_order",
}


class _RuleRejected(ValueError):
    """Internal static identifier, never provider/user text."""


def _write_rule(error: ValidationError, stage: str) -> str:
    # Inspect in memory only. Never log Pydantic's errors(), message or input:
    # those can include the entire private proposal and evidence.
    for detail in error.errors(include_input=False, include_url=False):
        if detail["type"] == "timezone_aware":
            return stage + "_timezone"
        if detail["type"] in {"greater_than", "less_than_equal", "int_type"}:
            return stage + "_resource_id"
        cause = detail.get("ctx", {}).get("error")
        if isinstance(cause, ValueError) and str(cause) in _WRITE_RULES:
            return _WRITE_RULES[str(cause)]
    return stage + "_constraints"


def _record_rejection(rule: str) -> None:
    _logger.warning("ai_proposal_rejected rule=%s code=%s", rule, _SAFE_CODE)


def validate_proposal(
    proposal: PlanProposal, context: AcademicContext
) -> tuple[StudyPlanWrite, list[StudyChallengeWrite]]:
    stage = "plan"
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
        has_resources = (
            bool(data.subject_ids)
            and set(data.subject_ids) <= context.subject_ids
            and set(data.activity_ids) <= context.activity_ids
            and set(data.study_session_ids) <= context.session_ids
        )
        viable = DecisionRoute().evaluate(
            has_resources=has_resources,
            valid_dates=data.end_at > data.start_at,
            enough_context=bool(context.subjects),
        )
        if viable != "propose":
            raise _RuleRejected(
                "owned_plan_resources"
                if not has_resources
                else "plan_context_required"
            )
        subjects = {row.id: row for row in context.subjects}
        activities = {row.id: row for row in context.activities}
        sessions = {row.id: row for row in context.sessions}
        challenges: list[StudyChallengeWrite] = []
        seen: set[tuple[str, int | None, int | None, int | None]] = set()
        for candidate in proposal.proposed_challenges:
            if not candidate.evidence or not candidate.measurable_condition:
                raise _RuleRejected("challenge_evidence_and_condition")
            if candidate.target_type == "custom":
                raise _RuleRejected("ai_custom_target_forbidden")
            if any(
                instant is not None and instant.utcoffset() is None
                for instant in (candidate.start_at, candidate.deadline)
            ):
                raise _RuleRejected("challenge_timezone")
            if (
                candidate.start_at is not None
                and not data.start_at <= candidate.start_at <= data.end_at
            ) or (
                candidate.deadline is not None
                and not data.start_at <= candidate.deadline <= data.end_at
            ):
                raise _RuleRejected("challenge_dates_in_plan")
            subject_id = candidate.subject_id
            activity_id = candidate.activity_id
            session_id = candidate.session_id
            if subject_id is None or subject_id not in data.subject_ids:
                raise _RuleRejected("challenge_subject_in_plan")
            if activity_id is not None and (
                activity_id not in data.activity_ids
                or activities[activity_id].subject_id != subject_id
            ):
                raise _RuleRejected("challenge_activity_relation")
            if session_id is not None and (
                session_id not in data.study_session_ids
                or sessions[session_id].subject_id != subject_id
                or (
                    activity_id is not None
                    and sessions[session_id].activity_id != activity_id
                )
            ):
                raise _RuleRejected("challenge_session_relation")
            if candidate.target_id is not None and candidate.target_id not in {
                subject_id,
                activity_id,
                session_id,
            }:
                raise _RuleRejected("challenge_target_relation")
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
                raise _RuleRejected("challenge_target_type_id")
            key = (candidate.target_type, subject_id, activity_id, session_id)
            if key in seen:
                raise _RuleRejected("unique_challenge")
            seen.add(key)
            if subject_id not in subjects:
                raise _RuleRejected("known_subject")
            linked_evidence = {
                f"subject:{subject_id}",
                f"activity:{activity_id}",
                f"session:{session_id}",
            }
            if any(
                token not in context.evidence_catalog for token in candidate.evidence
            ):
                raise _RuleRejected("catalog_evidence")
            if not any(token in linked_evidence for token in candidate.evidence):
                raise _RuleRejected("linked_evidence")
            if not (
                any(row.subject_id == subject_id for row in context.activities)
                or any(row.subject_id == subject_id for row in context.sessions)
            ):
                raise _RuleRejected("challenge_context_records")
            stage = "challenge"
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
    except _RuleRejected as exc:
        _record_rejection(str(exc))
        raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE") from None
    except ValidationError as exc:
        _record_rejection(_write_rule(exc, stage))
        raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE") from None
    except (KeyError, ValueError):
        _record_rejection("proposal_context_inconsistent")
        raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE") from None
