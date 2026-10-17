"""Exercise the actual launcher over TCP, including an installed wheel in CI."""

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]


def test_launcher_serves_registered_routes_over_http(pg_settings, tmp_path):
    interpreter = os.environ.get("COGNOVA_RUNTIME_PYTHON", sys.executable)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "LANG"}
    }
    environment.update(
        ENVIRONMENT="test",
        DATABASE_URL=pg_settings.database_url.get_secret_value(),
        JWT_SECRET=pg_settings.jwt_secret.get_secret_value(),
        COOKIE_SECURE="true",
        CORS_ALLOWED_ORIGINS="[]",
        PYTHONDONTWRITEBYTECODE="1",
    )
    probe = subprocess.run(
        [interpreter, str(ROOT / "scripts/inspect_runtime.py")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode == 0, "Runtime import inspection failed (output redacted)"
    evidence = json.loads(probe.stdout)
    print(json.dumps(evidence))  # Paths/versions only; no settings or credentials.
    assert evidence["openapi_url"] == "/openapi.json"
    assert {"/api/v1/health", "/api/v1/ready", "/api/v1/auth/me"} <= set(
        evidence["routes"]
    )
    for module, source in (
        ("app", "app/__init__.py"),
        ("app.main", "app/main.py"),
        ("app.api.router", "app/api/router.py"),
    ):
        actual = evidence["modules"][module]
        expected = (ROOT / source).read_bytes().replace(b"\r\n", b"\n")
        assert actual["sha256"] == hashlib.sha256(expected).hexdigest()
        if "COGNOVA_RUNTIME_PYTHON" in os.environ:
            assert Path(actual["file"]).is_relative_to(Path(evidence["prefix"]))
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment["PORT"] = str(port)
    process = subprocess.Popen(
        [interpreter, str(ROOT / "scripts/start.py")],
        cwd=tmp_path,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2) as client:
            deadline = time.monotonic() + 30
            while True:
                assert process.poll() is None, "Launcher exited before serving"
                try:
                    response = client.get("/openapi.json")
                    break
                except httpx.ConnectError:
                    assert time.monotonic() < deadline, "Launcher did not listen"
                    time.sleep(0.1)
            assert response.status_code == 200
            assert set(response.json()["paths"]) == set(evidence["routes"])
            assert client.get("/api/v1/health").json() == {"status": "ok"}
            ready = client.get("/api/v1/ready")
            assert ready.status_code == 200
            assert ready.json() == {"status": "ready"}
            me = client.get("/api/v1/auth/me")
            assert me.status_code == 401  # Registered and protected, not 404.
            assert me.headers["X-Request-ID"]
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
