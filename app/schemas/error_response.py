from pydantic import BaseModel

from app.schemas.error_detail import ErrorDetail


class ErrorResponse(BaseModel):
    error: ErrorDetail
