import pytest
from pydantic import ValidationError

from app.questionnaire.catalog import BY_ID
from app.schemas.questionnaire_request import QuestionnaireRequest
from app.tests.questionnaire_samples import questionnaire_payload


@pytest.mark.parametrize("question", [f"q{i}" for i in range(1, 11)])
def test_each_question_is_required(question):
    payload = questionnaire_payload()
    del payload["answers"][question]
    with pytest.raises(ValidationError):
        QuestionnaireRequest.model_validate(payload)


@pytest.mark.parametrize("question", ["q6", "q7", "q10"])
@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_multi_cardinalities(question, count):
    payload = questionnaire_payload()
    payload["answers"][question]["choices"] = [
        option.id for option in BY_ID[question].options[:count]
    ]
    if 1 <= count <= BY_ID[question].max_choices:
        QuestionnaireRequest.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            QuestionnaireRequest.model_validate(payload)


@pytest.mark.parametrize("question", ["q1", "q2", "q3", "q4", "q5", "q8", "q9"])
def test_single_rejects_multiple(question):
    payload = questionnaire_payload()
    payload["answers"][question]["choices"] = [
        o.id for o in BY_ID[question].options[:2]
    ]
    with pytest.raises(ValidationError):
        QuestionnaireRequest.model_validate(payload)


@pytest.mark.parametrize(
    "choices", [["unknown"], ["distractions", "distractions"], [1], "distractions"]
)
def test_rejects_unknown_duplicate_or_wrong_types(choices):
    payload = questionnaire_payload()
    payload["answers"]["q6"]["choices"] = choices
    with pytest.raises(ValidationError):
        QuestionnaireRequest.model_validate(payload)


@pytest.mark.parametrize("question", ["q1", "q6", "q7"])
@pytest.mark.parametrize(
    "text", [None, "", "   ", "a" * 51, "  válido: otro  ", "a" * 50]
)
def test_other_text(question, text):
    payload = questionnaire_payload()
    payload["answers"][question] = {"choices": ["other"], "other_text": text}
    if text is not None and 1 <= len(text.strip()) <= 50:
        result = QuestionnaireRequest.model_validate(payload)
        assert getattr(result.answers, question).other_text == text.strip()
    else:
        with pytest.raises(ValidationError):
            QuestionnaireRequest.model_validate(payload)


def test_forbids_unselected_other_extra_questions_and_extra_fields():
    for mutation in ("other", "question", "owner"):
        payload = questionnaire_payload()
        if mutation == "other":
            payload["answers"]["q1"]["other_text"] = "unselected"
        elif mutation == "question":
            payload["answers"]["q11"] = {"choices": ["unknown"]}
        else:
            payload["user_id"] = 123
        with pytest.raises(ValidationError):
            QuestionnaireRequest.model_validate(payload)


@pytest.mark.parametrize("version", [True, "1", 1.0, 2])
def test_catalog_version_is_exact_integer(version):
    with pytest.raises(ValidationError):
        QuestionnaireRequest.model_validate(
            {**questionnaire_payload(), "questionnaire_version": version}
        )
