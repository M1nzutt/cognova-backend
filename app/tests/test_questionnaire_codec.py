import pytest

from app.questionnaire.codec import decode_answers, encode_answers
from app.schemas.questionnaire_request import QuestionnaireRequest
from app.tests.questionnaire_samples import questionnaire_payload


def test_codec_round_trip_preserves_other_text_and_choice_order():
    payload = questionnaire_payload()
    for question in ("q1", "q6", "q7"):
        payload["answers"][question] = {"choices": ["other"], "other_text": "texto: ñ"}
    answers = QuestionnaireRequest.model_validate(payload).answers
    encoded = encode_answers(answers)
    assert encoded["q1"] == "other:texto: ñ"
    assert encoded["q6"] == ["other:texto: ñ"]
    assert decode_answers(encoded, 1) == answers
    assert len(encoded) == 10


def test_invalid_persistent_snapshot_is_not_accepted_as_complete():
    encoded = encode_answers(
        QuestionnaireRequest.model_validate(questionnaire_payload()).answers
    )
    for changed in (
        {**encoded, "q1": ["organize_time"]},
        {**encoded, "q6": "distractions"},
        {**encoded, "q1": "other:"},
    ):
        with pytest.raises(ValueError):
            decode_answers(changed, 1)
    with pytest.raises(ValueError):
        decode_answers(encoded, 2)
