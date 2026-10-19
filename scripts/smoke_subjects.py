"""Live subjects smoke: retains two synthetic users; never logs credentials."""

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from scripts.smoke_auth import check_onboarding


def check(response, expected, label, report, code=None):
    if response.status_code != expected:
        raise RuntimeError(f"{label}: expected {expected}, got {response.status_code}")
    if "no-store" not in response.headers.get("cache-control", "").lower():
        raise RuntimeError(f"{label}: missing no-store")
    if code and response.json().get("error", {}).get("code") != code:
        raise RuntimeError(f"{label}: unexpected error code")
    if code and set(response.json()) != {"error"}:
        raise RuntimeError(f"{label}: unexpected error envelope")
    report["checks"][label] = {"status": expected, "no_store": True}
    if code:
        report["checks"][label]["code"] = code
    print(f"{label}: {expected}")
    return response.json() if response.content else None


def register(client, label, report):
    payload = {
        "name": "Subjects release smoke",
        "email": f"subjects-{secrets.token_hex(10)}@example.com",
        "password": secrets.token_urlsafe(9),
    }
    body = check(
        client.post("/api/v1/auth/register", json=payload),
        201,
        label + " register",
        report,
    )
    first_access = body["access_token"]
    uid = body["user"]["id"]
    client.headers["Authorization"] = "Bearer " + first_access
    check(
        client.get("/api/v1/subjects/catalog"),
        403,
        label + " onboarding gate",
        report,
        "ONBOARDING_REQUIRED",
    )
    body = check(
        client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        ),
        200,
        label + " login",
        report,
    )
    client.headers["Authorization"] = "Bearer " + body["access_token"]
    check_onboarding(client, {"Authorization": client.headers["Authorization"]})
    report["checks"][label + " onboarding history"] = "passed; revisions 1/2"
    cookies = {cookie.name: cookie for cookie in client.cookies.jar}
    refresh, csrf = cookies["cognova_refresh"], cookies["cognova_csrf"]
    assert refresh.secure and csrf.secure
    assert refresh.has_nonstandard_attr("HttpOnly")
    assert not csrf.has_nonstandard_attr("HttpOnly")
    assert refresh.path == "/api/v1/auth" and csrf.path == "/"
    assert not refresh.domain_specified and not csrf.domain_specified
    assert all(
        str(c.get_nonstandard_attr("SameSite")).lower() == "lax"
        for c in (refresh, csrf)
    )
    report["checks"][label + " cookie attributes"] = "passed"
    old_refresh = refresh.value
    check(
        client.post("/api/v1/auth/refresh"),
        403,
        label + " csrf rejection",
        report,
        "CSRF_VALIDATION_FAILED",
    )
    body = check(
        client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf.value}),
        200,
        label + " refresh",
        report,
    )
    assert client.cookies.get("cognova_refresh") != old_refresh
    client.headers["Authorization"] = "Bearer " + body["access_token"]
    check(client.get("/api/v1/auth/me"), 200, label + " me after refresh", report)
    sessions = check(
        client.get("/api/v1/auth/sessions"), 200, label + " sessions", report
    )
    for session in sessions:
        if not session["current"]:
            check(
                client.delete(f"/api/v1/auth/sessions/{session['id']}"),
                204,
                label + " revoke other session",
                report,
            )
    check(
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + first_access}
        ),
        401,
        label + " revoked access",
        report,
        "SESSION_REVOKED",
    )
    return uid


def subjects(a, b, report, expected_delete):
    root = "/api/v1/subjects"

    def request(client, method, path, expected, label, code=None, **kwargs):
        return check(
            client.request(method, root + path, **kwargs), expected, label, report, code
        )

    catalog = request(a, "GET", "/catalog", 200, "catalog")
    assert catalog["version"] == 1 and len(catalog["color_bases"]) == 10
    assert catalog["color_shades"] == [100, 200, 300, 400, 500]
    data = {
        "name": "Smoke Algebra",
        "difficulty": "medium",
        "color_base": "blue",
        "color_shade": 300,
    }
    first = request(a, "POST", "", 201, "create", json=data)
    sid = first["id"]
    assert "user_id" not in first and "active_slot" not in first
    listed = request(a, "GET", "", 200, "list")
    assert [s["id"] for s in listed["items"]] == [sid]
    assert request(a, "GET", f"/{sid}", 200, "detail") == first
    edited = {**data, "name": "Smoke Calculus", "difficulty": "hard"}
    changed = request(a, "PUT", f"/{sid}", 200, "edit", json=edited)
    assert changed["name"] == edited["name"] and changed["id"] == sid
    assert changed["created_at"] == first["created_at"]
    archived = request(a, "POST", f"/{sid}/archive", 200, "archive")
    assert archived["status"] == "archived" and archived["id"] == sid
    request(
        a,
        "POST",
        "",
        409,
        "archived name reserved",
        "SUBJECT_NAME_CONFLICT",
        json={**edited, "name": "smoke calculus"},
    )
    assert (
        request(a, "POST", f"/{sid}/reactivate", 200, "reactivate")["status"]
        == "active"
    )
    request(a, "POST", "", 409, "duplicate", "SUBJECT_NAME_CONFLICT", json=edited)
    other = request(b, "POST", "", 201, "same name another user", json=edited)
    assert other["id"] != sid
    missing = request(b, "GET", "/2147483647", 404, "missing", "SUBJECT_NOT_FOUND")
    for method, suffix, kwargs in (
        ("GET", "", {}),
        ("PUT", "", {"json": edited}),
        ("POST", "/archive", {}),
        ("POST", "/reactivate", {}),
        ("DELETE", "?confirm=true", {}),
    ):
        body = request(
            b,
            method,
            f"/{sid}{suffix}",
            404,
            "ownership " + method + suffix,
            "SUBJECT_NOT_FOUND",
            **kwargs,
        )
        assert body == missing
    assert [
        s["id"] for s in request(b, "GET", "?status=all", 200, "isolated list")["items"]
    ] == [other["id"]]
    for n in range(2, 6):
        request(
            a,
            "POST",
            "",
            201,
            f"create active {n}",
            json={**data, "name": f"Smoke Subject {n}"},
        )
    request(
        a,
        "POST",
        "",
        409,
        "sixth active",
        "SUBJECT_ACTIVE_LIMIT",
        json={**data, "name": "Smoke Sixth"},
    )
    extra = request(
        a,
        "POST",
        "",
        201,
        "archived outside capacity",
        json={**data, "name": "Smoke Archived", "status": "archived"},
    )
    request(
        a,
        "POST",
        f"/{extra['id']}/reactivate",
        409,
        "reactivation limit",
        "SUBJECT_REACTIVATION_LIMIT",
    )
    request(a, "POST", f"/{sid}/archive", 200, "free active slot")
    request(a, "POST", f"/{extra['id']}/reactivate", 200, "reuse active slot")
    active = request(a, "GET", "", 200, "five active after transition")
    assert len(active["items"]) == 5
    request(
        a, "DELETE", f"/{sid}", 422, "delete confirmation required", "VALIDATION_ERROR"
    )
    before_delete = request(a, "GET", f"/{sid}", 200, "before delete")
    deleted = request(
        a,
        "DELETE",
        f"/{sid}?confirm=true",
        expected_delete,
        "explicit delete",
        "SERVICE_UNAVAILABLE" if expected_delete == 503 else None,
    )
    if expected_delete == 503:
        assert deleted == {
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": "Servicio temporalmente no disponible.",
            }
        }
        assert (
            request(a, "GET", f"/{sid}", 200, "delete rollback preserved row")
            == before_delete
        )
        report["delete"] = "blocked: HTTP 503 SERVICE_UNAVAILABLE; row unchanged"
    else:
        request(a, "GET", f"/{sid}", 404, "deleted absent", "SUBJECT_NOT_FOUND")
        report["delete"] = "passed: HTTP 204"
    report["synthetic_subject_ids"] = {
        "owner_subject": sid,
        "other_subject": other["id"],
        "reactivated": extra["id"],
    }
    # Retain synthetic records, but remove them from active listings through the API.
    for label, client in (("A", a), ("B", b)):
        rows = request(client, "GET", "?status=all", 200, label + " retained subjects")
        for row in rows["items"]:
            request(
                client,
                "POST",
                f"/{row['id']}/archive",
                200,
                f"{label} retain archived {row['id']}",
            )
        assert (
            request(client, "GET", "", 200, label + " no active fixtures")["items"]
            == []
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("--frontend-origin", required=True)
    parser.add_argument(
        "--expected-delete", type=int, choices=(204, 503), required=True
    )
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    parts = urlsplit(args.origin)
    if parts.scheme != "https" or not parts.hostname or parts.path:
        raise SystemExit("Use an HTTPS origin without a path")
    report = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "checks": {}}
    clients = [
        httpx.Client(
            base_url=args.origin,
            timeout=90,
            follow_redirects=False,
            headers={"Origin": args.frontend_origin},
        )
        for _ in range(2)
    ]
    try:
        a, b = clients
        check(a.get("/api/v1/health"), 200, "health", report)
        check(a.get("/api/v1/ready"), 200, "readiness", report)
        check(a.get("/api/v1/subjects/catalog"), 401, "catalog without bearer", report)
        schema = a.get("/openapi.json")
        assert schema.status_code == 200
        assert "delete" in schema.json()["paths"]["/api/v1/subjects/{subject_id}"]
        report["checks"]["openapi"] = "passed"
        report["synthetic_user_ids"] = [
            register(a, "A", report),
            register(b, "B", report),
        ]
        subjects(a, b, report, args.expected_delete)
        check(a.get("/api/v1/ready"), 200, "post-smoke readiness", report)
        report["status"] = (
            "passed_except_expected_delete" if args.expected_delete == 503 else "passed"
        )
    except Exception as error:
        report["status"] = "failed"
        report["failure_type"] = type(error).__name__
        # Only locally authored check errors contain safe status/step labels.
        if isinstance(error, RuntimeError):
            report["failed_check"] = str(error)
    finally:
        for label, client in zip(("A", "B"), clients):
            try:
                if client.cookies.get("cognova_refresh"):
                    check(
                        client.post(
                            "/api/v1/auth/logout",
                            headers={
                                "X-CSRF-Token": client.cookies.get("cognova_csrf", "")
                            },
                        ),
                        204,
                        label + " logout",
                        report,
                    )
                    check(
                        client.get("/api/v1/auth/me"),
                        401,
                        label + " logged out",
                        report,
                        "SESSION_REVOKED",
                    )
            except Exception as error:
                report["status"] = "failed"
                report[label + " cleanup_failure_type"] = type(error).__name__
            client.close()
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        args.evidence.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
