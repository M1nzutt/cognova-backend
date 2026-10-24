from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import DBAPIError

from app.core.domain_error import DomainError
from app.services.activity_service import ActivityService


def failure(state, constraint=None):
    return DBAPIError(
        "private SQL",
        {},
        SimpleNamespace(
            sqlstate=state, diag=SimpleNamespace(constraint_name=constraint)
        ),
    )


@pytest.mark.parametrize(
    "state,constraint",
    [
        ("40001", None),
        ("40P01", None),
    ],
)
def test_retry_rolls_back_and_restarts_whole_transaction(state, constraint):
    db = MagicMock()
    operation = MagicMock(side_effect=[failure(state, constraint), "result"])
    with patch("app.services.activity_service.time.sleep"):
        assert ActivityService(db)._write(1, operation) == "result"
    assert db.scalar.call_count == 2  # Reacquire owner lock, not only INSERT retry.
    assert db.rollback.call_count == 2
    db.commit.assert_called_once()
    assert operation.call_count == 2


def test_retry_is_bounded_and_does_not_expose_native_errors():
    db = MagicMock()
    with (
        patch("app.services.activity_service.time.sleep"),
        pytest.raises(DomainError) as e,
    ):
        ActivityService(db)._write(1, MagicMock(side_effect=failure("40001")))
    assert e.value.code == "ACTIVITY_WRITE_CONFLICT"
    assert "SQL" not in str(e.value)
    assert db.rollback.call_count == 4
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "state,constraint,deleting,code",
    [
        ("23503", "fk_activities_owner_subject", False, "SUBJECT_NOT_FOUND"),
        ("23503", "future_fk", True, "ACTIVITY_HAS_DEPENDENCIES"),
        ("23001", "restrict_fk", True, "ACTIVITY_HAS_DEPENDENCIES"),
    ],
)
def test_expected_constraints_translate_without_retry(
    state, constraint, deleting, code
):
    db = MagicMock()
    operation = MagicMock(side_effect=failure(state, constraint))
    with pytest.raises(DomainError) as e:
        ActivityService(db)._write(1, operation, deleting=deleting)
    assert e.value.code == code
    assert operation.call_count == 1
    assert db.rollback.call_count == 2


def test_ambiguous_commit_is_not_retried():
    db = MagicMock()
    db.commit.side_effect = failure("08006")
    operation = MagicMock(return_value="done")
    with pytest.raises(DBAPIError):
        ActivityService(db)._write(1, operation)
    operation.assert_called_once()
    assert db.rollback.call_count == 2
