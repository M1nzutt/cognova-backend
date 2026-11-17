import json
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.academic_intelligence.gemini_provider import GeminiProvider
from app.academic_intelligence.gemini_schemas import PlanProposal
from app.academic_intelligence.proposal_validation import validate_proposal
from app.core.domain_error import DomainError
from app.tests.test_gemini_plan_codec import context as context
from app.tests.test_gemini_plan_codec import payload as payload


def reject_case(payload, context, case):
    """Each mutation passes PlanProposal before exercising a business rule."""
    challenge = payload["proposed_challenges"][0]
    if case == "empty_subjects":
        payload["subject_ids"] = []
    elif case == "foreign_subject":
        payload["subject_ids"] = [999]
    elif case == "foreign_activity":
        payload["activity_ids"] = [999]
    elif case == "foreign_session":
        payload["session_ids"] = [999]
    elif case == "missing_context":
        context.subjects = []
    elif case == "duplicate_ids":
        payload["activity_ids"] *= 2
    elif case == "invalid_id":
        payload["subject_ids"] = [0]
    elif case == "invalid_text":
        payload["name"] = "private\x00text"
    elif case == "blank_text":
        payload["name"] = "   "
    elif case == "plan_dates":
        payload["end_date"] = payload["start_date"]
    elif case == "plan_timezone":
        payload["start_date"] = "2030-06-01T09:00:00"
    elif case == "custom":
        challenge["target_type"] = "custom"
    elif case == "challenge_timezone":
        challenge["deadline"] = "2030-06-03T09:00:00"
    elif case == "challenge_start_before":
        challenge["start_at"] = "2030-05-31T00:00:00Z"
    elif case == "challenge_end_after":
        challenge["deadline"] = "2030-06-08T00:00:00Z"
    elif case == "challenge_dates":
        challenge["start_at"] = "2030-06-06T00:00:00Z"
        challenge["deadline"] = "2030-06-05T00:00:00Z"
    elif case == "challenge_subject":
        challenge["subject_id"] = None
    elif case == "challenge_activity":
        challenge["activity_id"] = 999
    elif case == "activity_subject":
        context.activities[0].subject_id = 999
    elif case in {"challenge_session", "session_subject", "session_activity"}:
        challenge["session_id"] = 301
        if case != "challenge_session":
            payload["session_ids"] = [301]
            context.session_ids = {301}
            context.sessions = [
                SimpleNamespace(
                    id=301,
                    subject_id=999 if case == "session_subject" else 101,
                    activity_id=999 if case == "session_activity" else 201,
                )
            ]
    elif case == "target_unrelated":
        challenge["target_id"] = 999
    elif case == "target_type":
        challenge["target_id"] = 101
    elif case == "typed_target_contradiction":
        challenge.update(target_id=101, activity_id=201)
    elif case == "duplicate_challenge":
        payload["proposed_challenges"] *= 2
    elif case == "unknown_subject":
        context.subjects = [SimpleNamespace(id=999)]
    elif case == "invented_evidence":
        challenge["evidence"] = ["activity:999"]
    elif case == "unlinked_evidence":
        context.evidence_catalog["activity:202"] = "private catalog text"
        challenge["evidence"] = ["activity:202"]
    elif case == "no_context_records":
        challenge.update(
            target_type="study_minutes",
            target_value={"minutes": 15},
            activity_id=None,
            target_id=None,
            evidence=["subject:101"],
        )
        context.evidence_catalog["subject:101"] = "private catalog text"
        context.activities = []
    elif case == "missing_activity_row":
        context.activities = []
    elif case == "minutes":
        challenge.update(target_type="study_minutes", target_value={"minutes": 0})
    elif case == "activity_target":
        challenge["target_value"] = {"status": "completada"}
    elif case == "session_target":
        challenge.update(
            target_type="session_completion",
            activity_id=None,
            target_id=None,
            evidence=["subject:101"],
        )
        context.evidence_catalog["subject:101"] = "private catalog text"
    elif case == "mastery_target":
        challenge.update(
            target_type="subject_mastery",
            target_id=101,
            target_value={"criterion": "Practicar", "threshold": 101},
        )
    elif case == "target_size":
        challenge["target_value"] = {"private": "x" * 4096}
    elif case == "criteria_size":
        context.evidence_catalog["activity:201"] = "x" * 16385
    elif case == "non_json":
        challenge["target_value"] = {"minutes": float("nan")}
    elif case == "challenge_blank":
        challenge["title"] = "   "
    else:
        raise AssertionError(case)


CASES = [
    ("empty_subjects", "owned_plan_resources"),
    ("foreign_subject", "owned_plan_resources"),
    ("foreign_activity", "owned_plan_resources"),
    ("foreign_session", "owned_plan_resources"),
    ("missing_context", "plan_context_required"),
    ("duplicate_ids", "unique_resource_ids"),
    ("invalid_id", "plan_resource_id"),
    ("invalid_text", "text_controls"),
    ("blank_text", "plan_constraints"),
    ("plan_dates", "plan_date_order"),
    ("plan_timezone", "plan_timezone"),
    ("custom", "ai_custom_target_forbidden"),
    ("challenge_timezone", "challenge_timezone"),
    ("challenge_start_before", "challenge_dates_in_plan"),
    ("challenge_end_after", "challenge_dates_in_plan"),
    ("challenge_dates", "challenge_date_order"),
    ("challenge_subject", "challenge_subject_in_plan"),
    ("challenge_activity", "challenge_activity_relation"),
    ("activity_subject", "challenge_activity_relation"),
    ("challenge_session", "challenge_session_relation"),
    ("session_subject", "challenge_session_relation"),
    ("session_activity", "challenge_session_relation"),
    ("target_unrelated", "challenge_target_relation"),
    ("target_type", "challenge_target_type_id"),
    ("typed_target_contradiction", "challenge_target_type_id"),
    ("duplicate_challenge", "unique_challenge"),
    ("unknown_subject", "known_subject"),
    ("invented_evidence", "catalog_evidence"),
    ("unlinked_evidence", "linked_evidence"),
    ("no_context_records", "challenge_context_records"),
    ("missing_activity_row", "proposal_context_inconsistent"),
    ("minutes", "study_minutes_target"),
    ("activity_target", "activity_completion_target"),
    ("session_target", "session_completion_target"),
    ("mastery_target", "subject_mastery_target"),
    ("target_size", "target_value_size"),
    ("criteria_size", "criteria_size"),
    ("non_json", "json_compatible_values"),
    ("challenge_blank", "challenge_constraints"),
]


@pytest.mark.parametrize(("case", "rule"), CASES)
def test_structurally_valid_rejections_have_safe_named_rule(
    payload, context, case, rule, caplog
):
    reject_case(payload, context, case)
    proposal = PlanProposal.model_validate_json(json.dumps(payload), strict=True)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(DomainError) as exc:
            validate_proposal(proposal, context)
    assert exc.value.code == "STUDY_PLAN_GENERATION_UNAVAILABLE"
    assert [record.getMessage() for record in caplog.records] == [
        f"ai_proposal_rejected rule={rule} code=AI_PROPOSAL_RULE_REJECTED"
    ]
    assert all(record.exc_info is None for record in caplog.records)
    assert "private" not in caplog.text
    assert "activity:201" not in caplog.text
    assert payload["objective"] not in caplog.text


def test_valid_proposal_logs_no_rejection(payload, context, caplog):
    validate_proposal(PlanProposal.model_validate(payload), context)
    assert not caplog.records


@pytest.mark.parametrize(
    ("target_type", "value", "target_id"),
    [
        ("activity_completion", {"status": "completed"}, 201),
        ("activity_completion", {"status": "completed"}, None),
        ("study_minutes", {"minutes": 15}, 101),
        ("subject_mastery", {"criterion": "Practicar", "threshold": 80}, 101),
        ("session_completion", {"lifecycle": "finished"}, 301),
    ],
)
def test_documented_target_shapes_pass_business_validation(
    payload, context, target_type, value, target_id
):
    challenge = payload["proposed_challenges"][0]
    challenge.update(target_type=target_type, target_value=value, target_id=target_id)
    if target_type == "session_completion":
        challenge["session_id"] = 301
        payload["session_ids"] = [301]
        context.session_ids = {301}
        context.sessions = [SimpleNamespace(id=301, subject_id=101, activity_id=201)]
    validate_proposal(PlanProposal.model_validate(payload), context)


def test_empty_evidence_defense_is_named(payload, context, caplog):
    # Defense in depth: normal Pydantic parsing already rejects this input.
    proposal = PlanProposal.model_validate(payload)
    proposal.proposed_challenges[0].evidence = []
    with pytest.raises(DomainError):
        validate_proposal(proposal, context)
    assert "rule=challenge_evidence_and_condition " in caplog.text


def test_instruction_explains_ai_target_contract(payload):
    create = Mock(return_value=SimpleNamespace(
        status="completed", output_text=json.dumps(payload)
    ))
    GeminiProvider(
        None, client=SimpleNamespace(interactions=SimpleNamespace(create=create))
    ).plan("{}")
    instruction = create.call_args.kwargs["system_instruction"]
    for text in (
        "Never use target_type custom",
        '{"status":"completed"}',
        '{"lifecycle":"finished"}',
        '{"minutes":N}',
        '{"criterion":"nonempty text","threshold":N}',
        "Every challenge needs subject_id",
        "Set the optional generic target_id to null",
        "deadline must not precede start_at",
        "must lie within the plan dates",
    ):
        assert text in instruction
