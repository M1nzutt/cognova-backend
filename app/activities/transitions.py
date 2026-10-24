from app.core.domain_error import DomainError


def validate_transition(current: str, target: str) -> None:
    if current in {"completed", "cancelled"} and target not in {current, "pending"}:
        raise DomainError("ACTIVITY_TRANSITION_CONFLICT")
