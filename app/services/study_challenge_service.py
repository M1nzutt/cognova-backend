import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.study_plans import (
    StudyChallenge,
    StudyPlan,
    StudyPlanActivity,
    StudyPlanSession,
    StudyPlanSubject,
)
from app.models.study_session import StudySession
from app.models.user import User
from app.schemas.study_challenge_list_response import StudyChallengeListResponse
from app.schemas.study_challenge_response import StudyChallengeResponse
from app.schemas.study_challenge_write import StudyChallengeWrite
from app.study_plans.dependency_network import DependencyNetwork

T = TypeVar("T")


class StudyChallengeService:
    """Owns plan-scoped Challenge resource, dependency and state operations."""

    _TRANSITIONS = {
        "start": ({"pending"}, "in_progress"),
        "complete": ({"in_progress"}, "completed"),
        "fail": ({"in_progress"}, "failed"),
        "cancel": ({"pending", "in_progress"}, "cancelled"),
    }

    def __init__(
        self, db: Session, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._db = db
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def list(
        self, user_id: int, plan_id: int, limit: int, after_id: int | None
    ) -> StudyChallengeListResponse:
        self._owned_plan(user_id, plan_id)
        query = select(StudyChallenge).where(
            StudyChallenge.user_id == user_id,
            StudyChallenge.plan_id == plan_id,
        )
        if after_id is not None:
            query = query.where(StudyChallenge.id > after_id)
        rows = self._db.scalars(
            query.order_by(StudyChallenge.id).limit(limit + 1)
        ).all()
        page = rows[:limit]
        return StudyChallengeListResponse(
            items=[StudyChallengeResponse.model_validate(row) for row in page],
            next_after_id=page[-1].id if len(rows) > limit and page else None,
        )

    def detail(
        self, user_id: int, plan_id: int, challenge_id: int
    ) -> StudyChallengeResponse:
        return StudyChallengeResponse.model_validate(
            self._owned_challenge(user_id, plan_id, challenge_id)
        )

    def create(
        self, user_id: int, plan_id: int, data: StudyChallengeWrite
    ) -> StudyChallengeResponse:
        def insert() -> StudyChallengeResponse:
            plan = self._owned_plan(user_id, plan_id, lock=True)
            if plan.status not in {"draft", "active"}:
                raise DomainError("STUDY_PLAN_STATE_CONFLICT")
            self._validate_resources(user_id, plan_id, data)
            criteria = self._criteria(data)
            self._validate_dependencies(user_id, plan_id, data, exclude_id=None)
            challenge = StudyChallenge(
                user_id=user_id,
                plan_id=plan_id,
                subject_id=data.subject_id,
                activity_id=data.activity_id,
                study_session_id=data.study_session_id,
                title=data.title,
                description=data.description,
                target_type=data.target_type,
                target_value=data.target_value,
                start_at=data.start_at,
                deadline=data.deadline,
                status="pending",
                source="manual",
                generation_criteria=criteria,
            )
            self._db.add(challenge)
            self._db.flush()
            return StudyChallengeResponse.model_validate(challenge)

        return self._write(user_id, insert)

    def update(
        self,
        user_id: int,
        plan_id: int,
        challenge_id: int,
        data: StudyChallengeWrite,
    ) -> StudyChallengeResponse:
        def replace() -> StudyChallengeResponse:
            plan = self._owned_plan(user_id, plan_id, lock=True)
            challenge = self._owned_challenge(user_id, plan_id, challenge_id, lock=True)
            if plan.status not in {"draft", "active"}:
                raise DomainError("STUDY_PLAN_STATE_CONFLICT")
            if challenge.status != "pending":
                raise DomainError("STUDY_CHALLENGE_STATE_CONFLICT")
            self._validate_resources(user_id, plan_id, data)
            self._validate_dependencies(user_id, plan_id, data, exclude_id=challenge.id)
            challenge.subject_id = data.subject_id
            challenge.activity_id = data.activity_id
            challenge.study_session_id = data.study_session_id
            challenge.title = data.title
            challenge.description = data.description
            challenge.target_type = data.target_type
            challenge.target_value = data.target_value
            challenge.start_at = data.start_at
            challenge.deadline = data.deadline
            challenge.generation_criteria = self._criteria(data)
            challenge.updated_at = self._clock()
            self._db.flush()
            return StudyChallengeResponse.model_validate(challenge)

        return self._write(user_id, replace)

    def transition(
        self, user_id: int, plan_id: int, challenge_id: int, action: str
    ) -> StudyChallengeResponse:
        allowed, target = self._TRANSITIONS[action]

        def change() -> StudyChallengeResponse:
            plan = self._owned_plan(user_id, plan_id, lock=True)
            challenge = self._owned_challenge(user_id, plan_id, challenge_id, lock=True)
            if (
                plan.status not in {"draft", "active"}
                or challenge.status not in allowed
            ):
                raise DomainError("STUDY_CHALLENGE_STATE_CONFLICT")
            challenge.status = target
            challenge.updated_at = self._clock()
            self._db.flush()
            return StudyChallengeResponse.model_validate(challenge)

        return self._write(user_id, change)

    def _owned_plan(
        self, user_id: int, plan_id: int, *, lock: bool = False
    ) -> StudyPlan:
        query = select(StudyPlan).where(
            StudyPlan.id == plan_id, StudyPlan.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        plan = self._db.scalar(query.execution_options(populate_existing=True))
        if plan is None:
            raise DomainError("STUDY_PLAN_NOT_FOUND")
        return plan

    def _owned_challenge(
        self,
        user_id: int,
        plan_id: int,
        challenge_id: int,
        *,
        lock: bool = False,
    ) -> StudyChallenge:
        query = select(StudyChallenge).where(
            StudyChallenge.user_id == user_id,
            StudyChallenge.plan_id == plan_id,
            StudyChallenge.id == challenge_id,
        )
        if lock:
            query = query.with_for_update()
        challenge = self._db.scalar(query.execution_options(populate_existing=True))
        if challenge is None:
            raise DomainError("STUDY_CHALLENGE_NOT_FOUND")
        return challenge

    def _validate_resources(
        self, user_id: int, plan_id: int, data: StudyChallengeWrite
    ) -> None:
        if (
            data.subject_id is not None
            and self._db.scalar(
                select(StudyPlanSubject.subject_id).where(
                    StudyPlanSubject.user_id == user_id,
                    StudyPlanSubject.plan_id == plan_id,
                    StudyPlanSubject.subject_id == data.subject_id,
                )
            )
            is None
        ):
            raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        if data.activity_id is not None:
            subject_id = self._db.scalar(
                select(StudyPlanActivity.subject_id).where(
                    StudyPlanActivity.user_id == user_id,
                    StudyPlanActivity.plan_id == plan_id,
                    StudyPlanActivity.activity_id == data.activity_id,
                )
            )
            if subject_id is None or subject_id != data.subject_id:
                raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        if data.study_session_id is not None:
            session_context = self._db.execute(
                select(
                    StudyPlanSession.subject_id,
                    StudySession.activity_id,
                )
                .join(
                    StudySession,
                    StudySession.id == StudyPlanSession.study_session_id,
                )
                .where(
                    StudyPlanSession.user_id == user_id,
                    StudyPlanSession.plan_id == plan_id,
                    StudyPlanSession.study_session_id == data.study_session_id,
                    StudySession.user_id == user_id,
                )
            ).first()
            if session_context is None or session_context.subject_id != data.subject_id:
                raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
            if (
                data.activity_id is not None
                and session_context.activity_id != data.activity_id
            ):
                raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        if data.depends_on_activity_ids and data.activity_id is None:
            raise DomainError("STUDY_PLAN_DEPENDENCY_CONFLICT")

    @staticmethod
    def _criteria(data: StudyChallengeWrite) -> dict[str, Any]:
        criteria = dict(data.generation_criteria)
        if data.depends_on_activity_ids:
            criteria["depends_on_activity_ids"] = data.depends_on_activity_ids
        return criteria

    def _validate_dependencies(
        self,
        user_id: int,
        plan_id: int,
        data: StudyChallengeWrite,
        *,
        exclude_id: int | None,
    ) -> None:
        activity_ids = set(
            self._db.scalars(
                select(StudyPlanActivity.activity_id).where(
                    StudyPlanActivity.user_id == user_id,
                    StudyPlanActivity.plan_id == plan_id,
                )
            ).all()
        )
        network = DependencyNetwork()
        for activity_id in sorted(activity_ids):
            network.add_activity(activity_id)
        query = select(StudyChallenge).where(
            StudyChallenge.user_id == user_id,
            StudyChallenge.plan_id == plan_id,
        )
        if exclude_id is not None:
            query = query.where(StudyChallenge.id != exclude_id)
        challenges = self._db.scalars(query).all()
        edges: set[tuple[int, int]] = set()
        try:
            for challenge in challenges:
                self._add_dependencies(
                    network,
                    edges,
                    activity_ids,
                    challenge.activity_id,
                    challenge.generation_criteria.get("depends_on_activity_ids", []),
                )
            self._add_dependencies(
                network,
                edges,
                activity_ids,
                data.activity_id,
                data.depends_on_activity_ids,
            )
        except (TypeError, ValueError):
            raise DomainError("STUDY_PLAN_DEPENDENCY_CONFLICT") from None

    @staticmethod
    def _add_dependencies(
        network: DependencyNetwork,
        edges: set[tuple[int, int]],
        activity_ids: set[int],
        target_id: int | None,
        dependencies: object,
    ) -> None:
        if target_id is None:
            if dependencies:
                raise ValueError("Dependencies require a target activity")
            return
        if target_id not in activity_ids or not isinstance(dependencies, list):
            raise ValueError("Dependency activities must belong to the Plan")
        for dependency_id in dependencies:
            if type(dependency_id) is not int or dependency_id not in activity_ids:
                raise ValueError("Dependency activities must belong to the Plan")
            edge = (target_id, dependency_id)
            if edge in edges:
                continue
            network.add_dependency(target_id, dependency_id)
            edges.add(edge)

    def _write(self, user_id: int, operation: Callable[[], T]) -> T:
        self._db.rollback()
        for attempt in range(3):
            try:
                self._db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                owner = self._db.scalar(
                    select(User.id).where(User.id == user_id).with_for_update()
                )
                if owner is None:
                    raise DomainError("STUDY_PLAN_NOT_FOUND")
                result = operation()
                self._db.commit()
                return result
            except DomainError:
                self._db.rollback()
                raise
            except DBAPIError as exc:
                self._db.rollback()
                state = getattr(exc.orig, "sqlstate", None)
                if state in {"40001", "40P01"} and attempt < 2:
                    time.sleep(0.01 * (attempt + 1))
                    continue
                if state in {"40001", "40P01"}:
                    raise DomainError("STUDY_CHALLENGE_WRITE_CONFLICT") from None
                constraint = getattr(
                    getattr(exc.orig, "diag", None), "constraint_name", None
                )
                if constraint == "ck_study_challenges_target_value":
                    raise DomainError("STUDY_CHALLENGE_TARGET_CONFLICT") from None
                if constraint == "ck_study_challenges_status":
                    raise DomainError("STUDY_CHALLENGE_STATE_CONFLICT") from None
                if state in {"23503", "23505", "23514"}:
                    raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT") from None
                raise
            except Exception:
                self._db.rollback()
                raise
        raise AssertionError("unreachable")


__all__ = ["StudyChallengeService"]
