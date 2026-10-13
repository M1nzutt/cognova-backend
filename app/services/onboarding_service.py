from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.core.identity_limits import registration_identity_valid
from app.models.academic_goal_legacy import AcademicGoalLegacy
from app.models.questionnaire_response import QuestionnaireResponseRecord
from app.models.user import User
from app.questionnaire.codec import decode_answers
from app.schemas.academic_profile_request import AcademicProfileRequest
from app.schemas.legacy_academic_goal_response import LegacyAcademicGoalResponse
from app.schemas.onboarding_response import OnboardingResponse
from app.schemas.onboarding_status import OnboardingStatus
from app.schemas.user_response import UserResponse


class OnboardingService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def status(self, user: User) -> OnboardingResponse:
        academic = bool(
            user.degree_program
            and user.degree_program.strip()
            and user.semester
            and user.semester > 0
        )
        initial = self._db.get(QuestionnaireResponseRecord, (user.id, 1))
        questionnaire = False
        if initial is not None:
            try:
                decode_answers(initial.answers, initial.questionnaire_version)
                questionnaire = True
            except ValueError:
                # Imported/manual invalid data must never mark onboarding complete.
                pass
        return OnboardingResponse(
            status=OnboardingStatus.COMPLETE
            if academic and questionnaire
            else OnboardingStatus.INCOMPLETE,
            academic_profile_complete=academic,
            questionnaire_complete=questionnaire,
            next_step="academic_profile"
            if not academic
            else "questionnaire"
            if not questionnaire
            else "complete",
        )

    def user_response(self, user: User) -> UserResponse:
        legacy = self._db.get(AcademicGoalLegacy, user.id)
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            degree_program=user.degree_program,
            semester=user.semester,
            onboarding=self.status(user),
            legacy_academic_goal=LegacyAcademicGoalResponse(
                value=legacy.academic_goal, captured_at=legacy.captured_at
            )
            if legacy
            else None,
        )

    def save_academic_profile(
        self, user_id: int, data: AcademicProfileRequest
    ) -> UserResponse:
        user = self._db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise DomainError("ONBOARDING_REQUIRED")
        if not registration_identity_valid(user.name, user.email):
            raise DomainError("LEGACY_PROFILE_REMEDIATION_REQUIRED")
        user.degree_program, user.semester = data.degree_program, data.semester
        self._db.commit()
        return self.user_response(user)

    def require_complete(self, user: User) -> User:
        if self.status(user).status != OnboardingStatus.COMPLETE:
            raise DomainError("ONBOARDING_REQUIRED")
        return user
