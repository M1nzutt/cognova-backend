from sqlalchemy.orm import Session

from app.academic_intelligence.academic_context import AcademicContext
from app.academic_intelligence.gemini_provider import GeminiProvider
from app.academic_intelligence.gemini_schemas import BehaviorObservation
from app.core.domain_error import DomainError
from app.schemas.behavior_analysis_response import BehaviorAnalysisResponse


class BehaviorAnalysisService:
    def __init__(self, db: Session, provider: GeminiProvider) -> None:
        self._db = db
        self._provider = provider

    def analyze(self, user_id: int) -> BehaviorAnalysisResponse:
        context = AcademicContext(self._db, user_id)
        count = context.finished_count
        if count < 5:
            observations = (
                [
                    BehaviorObservation(
                        observation=(
                            f"Tienes {count} sesiones válidas finalizadas registradas."
                        ),
                        evidence=[
                            f"Se contaron {count} sesiones finalizadas con resultado "
                            "y duración real positiva."
                        ],
                        question="¿Qué te gustaría observar en tus próximas sesiones?",
                        confidence_basis=(
                            "Aún no hay cinco sesiones válidas para explorar "
                            "posibles patrones."
                        ),
                        related_subject_ids=[],
                        related_activity_ids=[],
                        related_session_ids=[],
                    )
                ]
                if count
                else []
            )
            return BehaviorAnalysisResponse(
                finished_session_count=count,
                pattern_eligible=False,
                observations=observations,
            )
        evidence = context.as_json()
        self._db.rollback()
        proposal = self._provider.behavior(evidence)
        for item in proposal.observations:
            lower = f"{item.observation} {item.question}".casefold()
            linked_evidence = (
                {f"subject:{identifier}" for identifier in item.related_subject_ids}
                | {f"activity:{identifier}" for identifier in item.related_activity_ids}
                | {f"session:{identifier}" for identifier in item.related_session_ids}
            )
            if (
                not item.question.endswith("?")
                or not set(item.related_subject_ids) <= context.subject_ids
                or not set(item.related_activity_ids) <= context.activity_ids
                or not set(item.related_session_ids) <= context.session_ids
                or len(item.evidence) == 0
                or any(token not in context.evidence_catalog for token in item.evidence)
                or (
                    linked_evidence
                    and not any(token in linked_evidence for token in item.evidence)
                )
                or any(
                    marker in lower
                    for marker in (
                        "diagnós",
                        "trastorno",
                        "depres",
                        "ansiedad",
                        "tdah",
                        "evitas porque",
                        "eres perezoso",
                        "eres incapaz",
                    )
                )
            ):
                raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE")
            item.evidence = [context.evidence_catalog[token] for token in item.evidence]
        return BehaviorAnalysisResponse(
            finished_session_count=count,
            pattern_eligible=True,
            observations=proposal.observations,
        )
