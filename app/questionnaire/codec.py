from app.questionnaire.catalog import BY_ID
from app.schemas.questionnaire_answers import QuestionnaireAnswers
from app.schemas.questionnaire_request import QuestionnaireRequest


def encode_answers(answers: QuestionnaireAnswers) -> dict[str, str | list[str]]:
    stored: dict[str, str | list[str]] = {}
    for question_id, question in BY_ID.items():
        answer = getattr(answers, question_id)
        values = [
            f"other:{answer.other_text}" if choice == "other" else choice
            for choice in answer.choices
        ]
        stored[question_id] = values[0] if question.selection == "single" else values
    return stored


def decode_answers(
    stored: dict[str, str | list[str]], version: int
) -> QuestionnaireAnswers:
    decoded = {}
    if set(stored) != set(BY_ID):
        raise ValueError("Invalid stored questionnaire keys")
    for question_id, question in BY_ID.items():
        value = stored[question_id]
        if question.selection == "single":
            if not isinstance(value, str):
                raise ValueError("Invalid stored single choice")
            values = [value]
        else:
            if not isinstance(value, list):
                raise ValueError("Invalid stored multi choice")
            values = value
        choices, other = [], None
        for item in values:
            if not isinstance(item, str):
                raise ValueError("Invalid stored option")
            if item.startswith("other:"):
                choices.append("other")
                other = item[len("other:") :]
            else:
                choices.append(item)
        decoded[question_id] = {"choices": choices, "other_text": other}
    return QuestionnaireRequest.model_validate(
        {"questionnaire_version": version, "answers": decoded}
    ).answers
