from app.questionnaire.catalog import QUESTIONS


def questionnaire_payload():
    return {
        "questionnaire_version": 1,
        "answers": {q.id: {"choices": [q.options[0].id]} for q in QUESTIONS},
    }
