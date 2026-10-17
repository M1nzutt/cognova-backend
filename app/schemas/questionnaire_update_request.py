from pydantic import Field

from app.schemas.questionnaire_request import QuestionnaireRequest


class QuestionnaireUpdateRequest(QuestionnaireRequest):
    expected_revision: int = Field(gt=0, le=2147483646, strict=True)
