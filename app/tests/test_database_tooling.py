from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from app.tests.database_tooling import database_checkout, migrate_test_schema


def test_wrong_database_revision_is_rejected_before_execution():
    with patch(
        "app.tests.database_tooling.subprocess.run",
        side_effect=[
            CompletedProcess([], 0, stdout="wrong-sha"),
            CompletedProcess([], 0, stdout=""),
        ],
    ):
        with pytest.raises(RuntimeError, match="clean checkout"):
            database_checkout()


def test_migration_errors_and_application_secrets_are_not_exposed(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "must-not-reach-migration-tool")
    with patch(
        "app.tests.database_tooling.subprocess.run",
        return_value=CompletedProcess([], 1, stdout=b"secret", stderr=b"secret"),
    ) as run:
        with pytest.raises(RuntimeError, match="output redacted") as error:
            migrate_test_schema(Path("unused"), "postgresql://private-password")
    assert "secret" not in str(error.value)
    assert "JWT_SECRET" not in run.call_args.kwargs["env"]
    assert "private-password" not in str(run.call_args.args[0])
