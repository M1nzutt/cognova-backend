from app.questionnaire import q1, q2, q3, q4, q5, q6, q7, q8, q9, q10
from app.schemas.questionnaire_catalog_response import QuestionnaireCatalogResponse
from app.schemas.questionnaire_question import QuestionnaireQuestion

QUESTIONS = tuple(
    QuestionnaireQuestion.model_validate(module.QUESTION)
    for module in (q1, q2, q3, q4, q5, q6, q7, q8, q9, q10)
)
BY_ID = {question.id: question for question in QUESTIONS}


def catalog_response() -> QuestionnaireCatalogResponse:
    return QuestionnaireCatalogResponse(questions=list(QUESTIONS))
