from pydantic import BaseModel

from app.schemas.questionnaire_response import QuestionnaireResponse


class QuestionnaireHistoryResponse(BaseModel):
    items: list[QuestionnaireResponse]
    next_before_revision: int | None
