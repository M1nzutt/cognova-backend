from unittest.mock import patch

import pytest

from scripts.start import main


def test_failed_migration_never_starts_server_or_logs_secrets(caplog):
    with (
        patch("scripts.start.migrate", side_effect=RuntimeError("private-db-secret")),
        patch("scripts.start.uvicorn.run") as run,
        pytest.raises(SystemExit, match="1"),
    ):
        main()
    run.assert_not_called()
    assert "startup_failed" in caplog.text
    assert "private-db-secret" not in caplog.text
