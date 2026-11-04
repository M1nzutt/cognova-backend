from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.error_response import ErrorResponse
from app.schemas.study_challenge_list_response import StudyChallengeListResponse
from app.schemas.study_challenge_response import StudyChallengeResponse
from app.schemas.study_challenge_write import StudyChallengeWrite
from app.schemas.study_plan_detail import StudyPlanDetail
from app.schemas.study_plan_list_response import StudyPlanListResponse
from app.schemas.study_plan_write import StudyPlanWrite
from app.services.study_challenge_service import StudyChallengeService
from app.services.study_plan_service import StudyPlanService

router = APIRouter(
    prefix="/study-plans",
    tags=["study-plans"],
    responses={
        code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)
    },
)
CurrentUser = Annotated[User, Depends(get_onboarded_user)]
PlanId = Annotated[int, Path(gt=0, le=2147483647)]
ChallengeId = Annotated[int, Path(gt=0, le=2147483647)]


def get_plan_service(
    db: Annotated[Session, Depends(get_session)],
) -> StudyPlanService:
    return StudyPlanService(db)


def get_challenge_service(
    db: Annotated[Session, Depends(get_session)],
) -> StudyChallengeService:
    return StudyChallengeService(db)


PlanService = Annotated[StudyPlanService, Depends(get_plan_service)]
ChallengeService = Annotated[StudyChallengeService, Depends(get_challenge_service)]


@router.get("", response_model=StudyPlanListResponse)
def list_plans(
    user: CurrentUser,
    service: PlanService,
    status: Literal["draft", "active", "completed", "abandoned", "all"] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
) -> StudyPlanListResponse:
    return service.list(user.id, status, limit, after_id)


@router.post("", status_code=201, response_model=StudyPlanDetail)
def create_plan(
    data: StudyPlanWrite, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.create(user.id, data)


@router.get("/{plan_id}", response_model=StudyPlanDetail)
def plan_detail(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.detail(user.id, plan_id)


@router.put("/{plan_id}", response_model=StudyPlanDetail)
def update_plan(
    plan_id: PlanId,
    data: StudyPlanWrite,
    user: CurrentUser,
    service: PlanService,
) -> StudyPlanDetail:
    return service.update(user.id, plan_id, data)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(
    plan_id: PlanId,
    user: CurrentUser,
    service: PlanService,
    confirm: Annotated[Literal["true"], Query(description="Confirm safe deletion")],
) -> Response:
    service.delete(user.id, plan_id)
    return Response(status_code=204)


@router.post("/{plan_id}/accept", response_model=StudyPlanDetail)
def accept_plan(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.accept(user.id, plan_id)


@router.post("/{plan_id}/reject", response_model=StudyPlanDetail)
def reject_plan(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.reject(user.id, plan_id)


@router.post("/{plan_id}/regenerate", response_model=StudyPlanDetail)
def regenerate_plan(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.regenerate(user.id, plan_id)


@router.post("/{plan_id}/activate", response_model=StudyPlanDetail)
def activate_plan(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.activate(user.id, plan_id)


@router.post("/{plan_id}/complete", response_model=StudyPlanDetail)
def complete_plan(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.complete(user.id, plan_id)


@router.post("/{plan_id}/abandon", response_model=StudyPlanDetail)
def abandon_plan(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.abandon(user.id, plan_id)


@router.post("/{plan_id}/undo", response_model=StudyPlanDetail)
def undo_plan_edit(
    plan_id: PlanId, user: CurrentUser, service: PlanService
) -> StudyPlanDetail:
    return service.undo(user.id, plan_id)


@router.get("/{plan_id}/challenges", response_model=StudyChallengeListResponse)
def list_challenges(
    plan_id: PlanId,
    user: CurrentUser,
    service: ChallengeService,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
) -> StudyChallengeListResponse:
    return service.list(user.id, plan_id, limit, after_id)


@router.post(
    "/{plan_id}/challenges", status_code=201, response_model=StudyChallengeResponse
)
def create_challenge(
    plan_id: PlanId,
    data: StudyChallengeWrite,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.create(user.id, plan_id, data)


@router.get(
    "/{plan_id}/challenges/{challenge_id}", response_model=StudyChallengeResponse
)
def challenge_detail(
    plan_id: PlanId,
    challenge_id: ChallengeId,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.detail(user.id, plan_id, challenge_id)


@router.put(
    "/{plan_id}/challenges/{challenge_id}", response_model=StudyChallengeResponse
)
def update_challenge(
    plan_id: PlanId,
    challenge_id: ChallengeId,
    data: StudyChallengeWrite,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.update(user.id, plan_id, challenge_id, data)


@router.post(
    "/{plan_id}/challenges/{challenge_id}/start",
    response_model=StudyChallengeResponse,
)
def start_challenge(
    plan_id: PlanId,
    challenge_id: ChallengeId,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.transition(user.id, plan_id, challenge_id, "start")


@router.post(
    "/{plan_id}/challenges/{challenge_id}/complete",
    response_model=StudyChallengeResponse,
)
def complete_challenge(
    plan_id: PlanId,
    challenge_id: ChallengeId,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.transition(user.id, plan_id, challenge_id, "complete")


@router.post(
    "/{plan_id}/challenges/{challenge_id}/fail",
    response_model=StudyChallengeResponse,
)
def fail_challenge(
    plan_id: PlanId,
    challenge_id: ChallengeId,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.transition(user.id, plan_id, challenge_id, "fail")


@router.post(
    "/{plan_id}/challenges/{challenge_id}/cancel",
    response_model=StudyChallengeResponse,
)
def cancel_challenge(
    plan_id: PlanId,
    challenge_id: ChallengeId,
    user: CurrentUser,
    service: ChallengeService,
) -> StudyChallengeResponse:
    return service.transition(user.id, plan_id, challenge_id, "cancel")


__all__ = ["router"]
