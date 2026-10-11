from unittest.mock import patch

import pytest

from app.core.settings import Settings
from scripts.start import main, require_compatible_database


def test_unavailable_database_never_starts_server_or_logs_secrets(caplog):
    with (
        patch(
            "scripts.start.require_compatible_database",
            side_effect=RuntimeError("private-db-secret"),
        ),
        patch("scripts.start.uvicorn.run") as run,
        pytest.raises(SystemExit, match="1"),
    ):
        main()
    run.assert_not_called()
    assert "startup_failed" in caplog.text
    assert "private-db-secret" not in caplog.text


def test_incompatible_database_disposes_pool_and_never_listens():
    with (
        patch("scripts.start.Database") as database,
        patch("scripts.start.ReadinessService.check", return_value=False),
        patch("scripts.start.uvicorn.run") as run,
        pytest.raises(SystemExit),
    ):
        main()
    database.return_value.dispose.assert_called_once()
    run.assert_not_called()


def test_compatible_database_is_checked_and_pool_disposed_before_listening():
    events = []
    with (
        patch("scripts.start.Database") as database,
        patch("scripts.start.ReadinessService.check", return_value=True),
        patch(
            "scripts.start.uvicorn.run",
            side_effect=lambda *a, **k: events.append("listen"),
        ),
    ):
        database.return_value.dispose.side_effect = lambda: events.append("dispose")
        main()
    assert events == ["dispose", "listen"]


def test_connection_error_still_disposes_startup_pool():
    with (
        patch("scripts.start.Database") as database,
        patch("scripts.start.ReadinessService.check", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        require_compatible_database(Settings(_env_file=None))
    database.return_value.dispose.assert_called_once()
