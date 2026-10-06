from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.error_handlers import error_response
from app.services.readiness_service import ReadinessService

router = APIRouter(tags=["operations"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready(request: Request) -> dict[str, str] | JSONResponse:
    try:
        if ReadinessService(request.app.state.database).check():
            return {"status": "ready"}
    except SQLAlchemyError:
        pass
    return error_response(
        503, "SERVICE_UNAVAILABLE", "Servicio temporalmente no disponible."
    )
