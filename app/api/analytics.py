from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.overview_service import AnalyticsOverviewService
from app.analytics.search_service import AnalyticsSearchService
from app.analytics.study_time_service import AnalyticsStudyTimeService
from app.analytics.timeline_service import AnalyticsTimelineService
from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.analytics_overview import AnalyticsOverview
from app.schemas.analytics_search_filters import AnalyticsSearchFilters
from app.schemas.analytics_search_response import AnalyticsSearchResponse
from app.schemas.analytics_study_time_filters import AnalyticsStudyTimeFilters
from app.schemas.analytics_study_time_response import AnalyticsStudyTimeResponse
from app.schemas.analytics_timeline_filters import AnalyticsTimelineFilters
from app.schemas.analytics_timeline_response import AnalyticsTimelineResponse
from app.schemas.error_response import ErrorResponse

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 503)},
)


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    user: Annotated[User, Depends(get_onboarded_user)],
    db: Annotated[Session, Depends(get_session)],
) -> AnalyticsOverview:
    return AnalyticsOverviewService(db).get(user.id)


@router.get("/study-time", response_model=AnalyticsStudyTimeResponse)
def study_time(
    user: Annotated[User, Depends(get_onboarded_user)],
    db: Annotated[Session, Depends(get_session)],
    filters: Annotated[AnalyticsStudyTimeFilters, Query()],
) -> AnalyticsStudyTimeResponse:
    return AnalyticsStudyTimeService(db).get(user.id, filters)


@router.get("/timeline", response_model=AnalyticsTimelineResponse)
def timeline(
    user: Annotated[User, Depends(get_onboarded_user)],
    db: Annotated[Session, Depends(get_session)],
    filters: Annotated[AnalyticsTimelineFilters, Query()],
) -> AnalyticsTimelineResponse:
    return AnalyticsTimelineService(db).get_page(user.id, filters)


@router.get("/search", response_model=AnalyticsSearchResponse)
def search(
    user: Annotated[User, Depends(get_onboarded_user)],
    db: Annotated[Session, Depends(get_session)],
    filters: Annotated[AnalyticsSearchFilters, Query()],
) -> AnalyticsSearchResponse:
    return AnalyticsSearchService(db).search(user.id, filters)


__all__ = ["router"]
