from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router
from app.api.questionnaire import router as questionnaire_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(onboarding_router)
api_router.include_router(questionnaire_router)
