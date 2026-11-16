import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.academic_intelligence.gemini_plan_codec import (
    decode_plan_proposal,
    plan_generation_schema,
)
from app.academic_intelligence.gemini_provider import GeminiProvider
from app.academic_intelligence.gemini_schemas import PlanProposal
from app.academic_intelligence.proposal_validation import validate_proposal
from app.core.domain_error import DomainError
from app.services.study_plan_service import StudyPlanService


@pytest.fixture
def payload():
    return {
        "name": "Plan sintético",
        "objective": "Completar la práctica.",
        "start_date": "2030-06-01T09:00:00Z",
        "end_date": "2030-06-07T18:00:00Z",
        "explanation": "Existe una práctica pendiente.",
        "subject_ids": [101],
        "activity_ids": [201],
        "session_ids": [],
        "proposed_challenges": [
            {
                "title": "Completar práctica",
                "objective": "Terminar la actividad.",
                "explanation": "Está pendiente.",
                "evidence": ["activity:201"],
                "target_type": "activity_completion",
                "target_id": 201,
                "subject_id": 101,
                "activity_id": 201,
                "session_id": None,
                "target_value": {"status": "completed"},
                "measurable_condition": "Actividad completada.",
                "start_at": None,
                "deadline": "2030-06-07T18:00:00Z",
            }
        ],
        "reasoning_summary": "Una materia y una práctica pendiente.",
    }


@pytest.fixture
def context():
    return SimpleNamespace(
        subject_ids={101},
        activity_ids={201},
        session_ids=set(),
        subjects=[SimpleNamespace(id=101)],
        activities=[SimpleNamespace(id=201, subject_id=101)],
        sessions=[],
        evidence_catalog={"activity:201": "Práctica pendiente."},
        as_json=lambda: "{}",
    )


def test_generation_schema_keeps_every_field_and_internal_contract():
    original = PlanProposal.model_json_schema()
    before = deepcopy(original)
    wire = plan_generation_schema()
    assert PlanProposal.model_json_schema() == before
    assert set(wire["properties"]) == set(original["properties"])
    assert wire["required"] == original["required"]
    challenge = wire["properties"]["proposed_challenges"]["items"]
    internal = original["$defs"]["ProposedChallenge"]
    assert set(challenge["properties"]) == set(internal["properties"])
    assert challenge["required"] == internal["required"]
    assert challenge["properties"]["target_type"]["enum"] == (
        internal["properties"]["target_type"]["enum"]
    )
    assert challenge["properties"]["target_id"]["type"] == ["integer", "null"]
    assert challenge["additionalProperties"] is False
    assert challenge["properties"]["target_value"]["additionalProperties"] is True
    serialized = json.dumps(wire)
    for keyword in (
        "$defs", "$ref", "anyOf", "format", "maxItems", "minItems",
        "minLength", "maxLength", "default",
    ):
        assert f'"{keyword}"' not in serialized
    assert len(serialized) < len(json.dumps(original))


def test_valid_proposal_preserves_challenge_and_passes_business_rules(payload, context):
    proposal = decode_plan_proposal(json.dumps(payload))
    assert proposal.model_dump(mode="json")["proposed_challenges"][0][
        "target_value"
    ] == payload["proposed_challenges"][0]["target_value"]
    plan, challenges = validate_proposal(proposal, context)
    assert plan.activity_ids == [201]
    assert len(challenges) == 1


@pytest.mark.parametrize("field", list(PlanProposal.model_fields))
def test_missing_required_plan_field_is_rejected(payload, field):
    del payload[field]
    with pytest.raises(ValidationError):
        decode_plan_proposal(json.dumps(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", 12),
        ("name", ""),
        ("name", "x" * 101),
        ("subject_ids", ["101"]),
        ("subject_ids", [True]),
        ("subject_ids", [1.0]),
        ("subject_ids", list(range(101))),
        ("activity_ids", list(range(201))),
        ("start_date", "not-a-date"),
        ("proposed_challenges", [{}]),
        ("proposed_challenges", None),
    ],
)
def test_internal_constraints_still_reject_invalid_values(payload, field, value):
    payload[field] = value
    with pytest.raises(ValidationError):
        decode_plan_proposal(json.dumps(payload))


@pytest.mark.parametrize("kind", ["missing", "extra", "enum", "evidence", "length"])
def test_invalid_nested_challenge_is_rejected(payload, kind):
    challenge = payload["proposed_challenges"][0]
    if kind == "missing":
        del challenge["measurable_condition"]
    elif kind == "extra":
        challenge["unexpected"] = True
    elif kind == "enum":
        challenge["target_type"] = "invented"
    elif kind == "evidence":
        challenge["evidence"] = ["activity:201"] * 6
    else:
        payload["proposed_challenges"] *= 31
    with pytest.raises(ValidationError):
        decode_plan_proposal(json.dumps(payload))


@pytest.mark.parametrize("kind", ["owner", "relationship", "evidence", "dates", "zone"])
def test_business_validation_rejects_invalid_relations_and_dates(
    payload, context, kind
):
    if kind == "owner":
        payload["subject_ids"] = [999]
    elif kind == "relationship":
        context.activities[0].subject_id = 999
    elif kind == "evidence":
        payload["proposed_challenges"][0]["evidence"] = ["activity:999"]
    elif kind == "dates":
        payload["end_date"] = "2030-05-01T00:00:00Z"
    else:
        payload["start_date"] = "2030-06-01T09:00:00"
    proposal = decode_plan_proposal(json.dumps(payload))
    with pytest.raises(DomainError):
        validate_proposal(proposal, context)


@pytest.mark.parametrize("status", ["incomplete", "requires_continuation", "failed"])
def test_provider_rejects_incomplete_status_even_with_valid_json(payload, status):
    fake = SimpleNamespace(
        interactions=SimpleNamespace(
            create=Mock(return_value=SimpleNamespace(
                output_text=json.dumps(payload), status=status
            ))
        )
    )
    with pytest.raises(DomainError):
        GeminiProvider(None, client=fake).plan("{}")
    assert fake.interactions.create.call_count == 1


@pytest.mark.parametrize("kind", ["missing", "wrong_type", "truncated", "relation"])
def test_invalid_response_never_enters_write_phase(payload, context, monkeypatch, kind):
    if kind == "missing":
        del payload["objective"]
    elif kind == "wrong_type":
        payload["subject_ids"] = ["101"]
    elif kind == "relation":
        payload["proposed_challenges"][0]["activity_id"] = 999
    text = json.dumps(payload)
    if kind == "truncated":
        text = text[:-8]
    client = SimpleNamespace(
        interactions=SimpleNamespace(
            create=Mock(
                return_value=SimpleNamespace(output_text=text, status="completed")
            )
        )
    )
    db = Mock()
    service = StudyPlanService(
        db, proposal_provider=GeminiProvider(None, client=client)
    )
    write = Mock(side_effect=AssertionError("Invalid proposal reached persistence"))
    monkeypatch.setattr(service, "_write", write)
    monkeypatch.setattr(
        "app.services.study_plan_service.AcademicContext", lambda *_: context
    )
    with pytest.raises(DomainError):
        service.generate(1)
    write.assert_not_called()
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_provider_uses_simplified_plan_schema_and_stateless_request(payload):
    create = Mock(return_value=SimpleNamespace(
        output_text=json.dumps(payload), status="completed"
    ))
    provider = GeminiProvider(
        None, client=SimpleNamespace(interactions=SimpleNamespace(create=create))
    )
    provider.plan("{}")
    request = create.call_args.kwargs
    assert request["response_format"]["schema"] == plan_generation_schema()
    assert request["store"] is False
    assert request["automatic_continuation"] is False
    assert request["model"] == "gemini-3.8-flash"
