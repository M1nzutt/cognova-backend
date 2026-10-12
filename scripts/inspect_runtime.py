"""Print import/routing evidence without settings values or database access."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path

import app
import app.api.router
import app.main


def main() -> None:
    application = app.main.create_app()
    modules = {}
    for module in (app, app.main, app.api.router):
        path = Path(module.__file__ or "").resolve()
        modules[module.__name__] = {
            "file": str(path),
            "sha256": hashlib.sha256(
                path.read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest(),
        }
    print(
        json.dumps(
            {
                "cwd": os.getcwd(),
                "sys_path": sys.path,
                "prefix": sys.prefix,
                "modules": modules,
                "versions": {
                    name: importlib.metadata.version(name)
                    for name in ("cognova-backend", "fastapi", "starlette", "uvicorn")
                },
                "routes": sorted(application.openapi()["paths"]),
                "openapi_url": application.openapi_url,
            }
        )
    )


if __name__ == "__main__":
    main()
