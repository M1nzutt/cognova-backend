from app.core.domain_error import DomainError

_PRE_EXECUTION_RESULTS = {"postponed", "cancelled"}


def require_planned(state: str) -> None:
    if state != "planned":
        raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")


def require_start(state: str) -> None:
    require_planned(state)


def require_pause(state: str) -> None:
    if state != "running":
        raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")


def require_resume(state: str) -> None:
    if state != "paused":
        raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")


def require_finish(state: str, result: str) -> None:
    if state in {"running", "paused"}:
        return
    if state == "planned" and result in _PRE_EXECUTION_RESULTS:
        return
    raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")
