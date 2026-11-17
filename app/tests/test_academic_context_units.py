from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.academic_intelligence.academic_context import AcademicContext


def test_actual_duration_seconds_are_converted_to_minutes():
    session = SimpleNamespace(status="partial", actual_duration=Decimal("840.000000"))
    assert AcademicContext._session_minutes(session) == 14
    assert AcademicContext._cancelled_minutes(session) is None


def test_cancelled_elapsed_seconds_are_not_study_minutes():
    session = SimpleNamespace(
        status="cancelled", actual_duration=Decimal("45662.422572")
    )
    assert AcademicContext._session_minutes(session) == 0
    assert AcademicContext._cancelled_minutes(session) == pytest.approx(
        45662.422572 / 60
    )
