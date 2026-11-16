"""Private state and HTTP-only client for demonstration preparation."""

import json
import os
import secrets
import subprocess
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)

from scripts.demo_scenario import IDENTITY


class DemoError(Exception):
    """Messages must never contain request/response bodies or credentials."""


def validate_origin(base: str) -> str:
    parts = urlsplit(base)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username or parts.password or parts.query or parts.fragment
        or parts.path not in {"", "/"}
        or (parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1"})
    ):
        raise DemoError("Use an HTTPS origin, or HTTP loopback for local preparation")
    return base.rstrip("/")


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "nt":
        result = subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r",
             os.environ["USERNAME"] + ":(OI)(CI)F"],
            capture_output=True,
        )
        if result.returncode:
            raise DemoError("Could not restrict private state directory permissions")
    else:
        path.chmod(0o700)


def private_write(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    if os.name != "nt":
        path.chmod(0o600)


def _dpapi(value: str, decrypt: bool = False) -> str:
    command = (
        "$v=[Console]::In.ReadToEnd();"
        + (
            "$s=ConvertTo-SecureString $v;"
            "$n=[System.Net.NetworkCredential]::new('', $s);"
            "[Console]::Out.Write($n.Password)"
            if decrypt else
            "$s=ConvertTo-SecureString $v -AsPlainText -Force;"
            "[Console]::Out.Write((ConvertFrom-SecureString $s))"
        )
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        input=value, capture_output=True, text=True,
    )
    if result.returncode:
        raise DemoError("Credential encryption/decryption failed")
    return result.stdout


def credentials(directory: Path, *, create: bool = False) -> dict:
    path = directory / ("credentials.dpapi" if os.name == "nt" else "credentials.json")
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        return json.loads(_dpapi(raw, True) if os.name == "nt" else raw)
    if not create:
        raise DemoError("Private credentials do not exist; run prepare first")
    value = {**IDENTITY, "password": secrets.token_urlsafe(9)}
    raw = json.dumps(value)
    private_write(path, (_dpapi(raw) if os.name == "nt" else raw).encode())
    return value


class Journal:
    def __init__(self, directory: Path, base: str, reference: str):
        self.path = directory / "progress.json"
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            "version": 1, "base": base, "reference": reference,
            "steps": {}, "ai_attempts": [], "user_id": None,
        }
        if self.data["base"] != base or self.data["reference"] != reference:
            raise DemoError(
                "State belongs to another origin/reference; do not rebase existing data"
            )
        self.save()

    def save(self):
        private_write(self.path, json.dumps(self.data, indent=2).encode())

    def begin(self, key: str):
        entry = self.data["steps"].get(key)
        if entry and entry["state"] == "pending":
            raise DemoError(
                f"Ambiguous unfinished operation {key}; reconcile before resending"
            )
        self.data["steps"][key] = {"state": "pending"}
        self.save()

    def done(self, key: str, identifier=None):
        self.data["steps"][key] = {"state": "done", "id": identifier}
        self.save()
        print("STEP_DONE=" + key, flush=True)

    def completed(self, key: str):
        return self.data["steps"].get(key, {}).get("state") == "done"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DemoError(
            "Redirect refused; credentials must stay on the configured origin"
        )


class Api:
    def __init__(self, base: str, secret: dict):
        self.base, self.secret = base, secret
        self.cookies = CookieJar()
        self.opener = build_opener(NoRedirect(), HTTPCookieProcessor(self.cookies))
        self.token, self.authenticated_at = "", 0

    def login(self, *, register: bool = False):
        try:
            result = self.request("POST", "auth/login", {
                "email": self.secret["email"], "password": self.secret["password"],
            }, authenticate=False)
        except DemoError as error:
            if not register or str(error) != "HTTP 401 at POST auth/login":
                raise
            result = self.request(
                "POST", "auth/register", self.secret, authenticate=False
            )
        if result["user"]["email"] != self.secret["email"]:
            raise DemoError("Authenticated identity mismatch")
        self.token = result["access_token"]
        self.authenticated_at = time.monotonic()
        return result["user"]

    def request(self, method: str, path: str, body=None, *, authenticate=True):
        if method == "DELETE" or not path or path.startswith(("/", "http")):
            raise DemoError("Unsafe demo request refused")
        if (
            authenticate and self.token
            and time.monotonic() - self.authenticated_at > 480
        ):
            self.login()
        headers = {"Origin": self.base, "Accept": "application/json"}
        if self.token and authenticate:
            headers["Authorization"] = "Bearer " + self.token
        for cookie in self.cookies:
            if cookie.name == "cognova_csrf":
                headers["X-CSRF-Token"] = unquote(cookie.value)
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base + "/api/v1/" + path, data=data,
                          headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=130) as response:
                return json.load(response) if response.status != 204 else None
        except HTTPError as error:
            raise DemoError(f"HTTP {error.code} at {method} {path}") from None
        except (OSError, ValueError):
            raise DemoError(
                f"No trustworthy response at {method} {path}; do not retry blindly"
            ) from None

    def items(self, path: str) -> list:
        route, _, query = path.partition("?")
        parameters = dict(parse_qsl(query))
        parameters["limit"] = 100
        result, seen = [], set()
        for _ in range(100):
            value = self.request("GET", route + "?" + urlencode(parameters))
            result.extend(value["items"])
            cursor = value.get("next_cursor")
            if not cursor and value.get("next_after_id") is not None:
                cursor = {"after_id": value["next_after_id"]}
            if not cursor:
                return result
            marker = json.dumps(cursor, sort_keys=True)
            if marker in seen:
                raise DemoError("Repeated pagination cursor; refusing incomplete data")
            seen.add(marker)
            parameters.update(cursor)
        raise DemoError("Demo pagination safety bound exceeded")

    def logout(self):
        self.request("POST", "auth/logout")
        self.token = ""
