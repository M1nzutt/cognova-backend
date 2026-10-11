"""Check the externally managed schema before listening; never execute DDL."""

import logging
import os

import uvicorn

from app.core.settings import Settings
from app.database.database import Database
from app.services.readiness_service import ReadinessService


def require_compatible_database(settings: Settings) -> None:
    database = Database(settings)
    try:
        if not ReadinessService(database).check():
            raise RuntimeError("Database schema unavailable or incompatible")
    finally:
        database.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        settings = Settings()
        port = int(os.environ.get("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid port")
        require_compatible_database(settings)
    except Exception as exc:
        # Configuration/DB exceptions can contain credentials; omit their text.
        logging.error("startup_failed exception_type=%s", type(exc).__name__)
        raise SystemExit(1) from None
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=port,
        access_log=False,
        proxy_headers=False,
        workers=1,
        timeout_keep_alive=5,
    )


if __name__ == "__main__":
    main()
