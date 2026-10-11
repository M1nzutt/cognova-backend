"""Test-only adapter to an immutable database checkout, never API runtime."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def database_checkout() -> Path:
    reference = json.loads((ROOT / "tools/database-ref.json").read_text())
    path = Path(
        os.environ.get("COGNOVA_DATABASE_PATH", ROOT / ".local/database-handoff")
    ).resolve()
    head = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    dirty = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if (
        head.returncode
        or dirty.returncode
        or head.stdout.strip() != reference["commit"]
        or dirty.stdout.strip()
        or not (path / "cognova_database/runner.py").is_file()
    ):
        raise RuntimeError("A clean checkout at tools/database-ref.json is required")
    return path


def migrate_test_schema(path: Path, url: str) -> None:
    # The fixture validates the disposable destination and creates its own schema.
    # Credentials go through environment, never argv or captured error messages.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "LANG"}
    }
    environment.update(
        DATABASE_URL=url,
        ENVIRONMENT="test",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(path),
    )
    result = subprocess.run(
        [sys.executable, "-m", "cognova_database", "upgrade", "head"],
        cwd=path,
        env=environment,
        capture_output=True,
        timeout=180,
    )
    if result.returncode:
        raise RuntimeError("Database test migration failed; output redacted")
