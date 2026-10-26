from fastapi import APIRouter

from app.api.activities import router as activities_router
from app.api.auth import router as auth_router
from app.api.calendar import router as calendar_router
from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router
from app.api.questionnaire import router as questionnaire_router
from app.api.subjects import router as subjects_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(onboarding_router)
api_router.include_router(questionnaire_router)
api_router.include_router(subjects_router)

api_router.include_router(activities_router)

api_router.include_router(calendar_router)
