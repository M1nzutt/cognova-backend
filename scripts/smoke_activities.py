"""Live Activities smoke with synthetic accounts and secret-free evidence."""

import argparse
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from urllib.parse import urlsplit

import httpx

from scripts.smoke_auth import check_onboarding
from scripts.smoke_subjects import check

ROOT = "/api/v1/activities"


def register(client, label, report):
    body = check(
        client.post(
            "/api/v1/auth/register",
            json={
                "name": "Activities release smoke",
                "email": f"act-{secrets.token_hex(10)}@example.com",
                "password": secrets.token_urlsafe(9),
            },
        ),
        201,
        label + " register",
        report,
    )
    client.headers["Authorization"] = "Bearer " + body["access_token"]
    check(
        client.get(ROOT), 403, label + " onboarding gate", report, "ONBOARDING_REQUIRED"
    )
    check_onboarding(client, {"Authorization": client.headers["Authorization"]})
    cookies = {c.name: c for c in client.cookies.jar}
    refresh, csrf = cookies["cognova_refresh"], cookies["cognova_csrf"]
    assert refresh.secure and csrf.secure and refresh.has_nonstandard_attr("HttpOnly")
    assert not csrf.has_nonstandard_attr("HttpOnly")
    assert refresh.path == "/api/v1/auth" and csrf.path == "/"
    assert not refresh.domain_specified and not csrf.domain_specified
    assert all(
        str(c.get_nonstandard_attr("SameSite")).lower() == "lax"
        for c in (refresh, csrf)
    )
    check(
        client.post("/api/v1/auth/refresh"),
        403,
        label + " csrf refresh rejected",
        report,
        "CSRF_VALIDATION_FAILED",
    )
    updated = check(
        client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf.value}),
        200,
        label + " refresh",
        report,
    )
    assert client.cookies.get("cognova_refresh") != refresh.value
    client.headers["Authorization"] = "Bearer " + updated["access_token"]
    check(client.get("/api/v1/auth/me"), 200, label + " authenticated", report)
    report["checks"][label + " secure cookies"] = "passed"
    return body["user"]["id"]


def activities(a, b, report):
    def request(client, method, path, status, label, code=None, **kwargs):
        return check(
            client.request(method, ROOT + path, **kwargs), status, label, report, code
        )

    subjects = []
    for label, client in (("A", a), ("B", b)):
        row = check(
            client.post(
                "/api/v1/subjects",
                json={
                    "name": "Activity smoke",
                    "difficulty": "medium",
                    "color_base": "blue",
                    "color_shade": 300,
                },
            ),
            201,
            label + " subject",
            report,
        )
        subjects.append(row["id"])
    report["synthetic_subject_ids"] = subjects
    data = {
        "title": "Activity smoke",
        "subject_id": subjects[0],
        "deadline": "2030-01-01T12:00:00Z",
        "priority": "medium",
        "status": "pending",
        "estimated_duration": 30,
        "notes": None,
    }
    first = request(a, "POST", "", 201, "create activity", json=data)
    aid = first["id"]
    path = f"/{aid}"
    report["retained_activity_id"] = aid
    original = first["original_deadline"]
    assert (
        first["deadline"] == original
        and first["deadline_revision"] == 0
        and "user_id" not in first
    )
    assert request(a, "GET", path, 200, "detail") == first
    assert request(a, "GET", "", 200, "list")["items"] == [first]
    edited = {
        **data,
        "title": "Edited activity",
        "notes": "Synthetic release evidence",
        "priority": "high",
    }
    changed = request(a, "PUT", path, 200, "edit", json=edited)
    assert (
        changed["title"] == edited["title"]
        and changed["deadline_revision"] == 0
        and changed["created_at"] == first["created_at"]
    )
    for label, params in (
        ("subject", {"subject_id": subjects[0]}),
        ("status", {"status": "pending"}),
        ("priority", {"priority": "high"}),
        ("deadline", {"deadline": data["deadline"]}),
        ("range", {"deadline_from": data["deadline"], "deadline_to": data["deadline"]}),
        (
            "combined",
            {
                "subject_id": subjects[0],
                "status": "pending",
                "priority": "high",
                "deadline": data["deadline"],
            },
        ),
    ):
        assert [
            r["id"]
            for r in request(a, "GET", "", 200, "filter " + label, params=params)[
                "items"
            ]
        ] == [aid]
    assert (
        request(a, "GET", "", 200, "filter excludes", params={"priority": "urgent"})[
            "items"
        ]
        == []
    )
    state = request(
        a,
        "PATCH",
        path + "/status",
        200,
        "in progress",
        json={"status": "in_progress", "expected_status": "pending"},
    )
    request(
        a,
        "PATCH",
        path + "/status",
        409,
        "stale status",
        "ACTIVITY_STATE_CONFLICT",
        json={"status": "completed", "expected_status": "pending"},
    )
    for revision, deadline, label in (
        (0, "2030-01-03T12:00:00Z", "postpone"),
        (1, "2030-01-02T12:00:00Z", "reschedule"),
    ):
        state = request(
            a,
            "PATCH",
            path + "/deadline",
            200,
            label,
            json={"deadline": deadline, "expected_revision": revision},
        )
        assert (
            state["original_deadline"] == original and state["status"] == "in_progress"
        )
        assert state["deadline_revision"] == revision + 1
    events = request(a, "GET", path + "/deadline-history", 200, "deadline history")[
        "items"
    ]
    assert [e["event_type"] for e in events] == ["postponed", "rescheduled"]
    assert (
        events[0]["previous_deadline"] == original
        and events[1]["previous_deadline"] == events[0]["new_deadline"]
    )
    same = request(
        a,
        "PATCH",
        path + "/deadline",
        200,
        "equivalent timezone no event",
        json={"deadline": "2030-01-02T07:00:00-05:00", "expected_revision": 2},
    )
    assert same["deadline_revision"] == 2
    barrier = Barrier(2)

    def competing(day):
        barrier.wait(timeout=10)
        return a.patch(
            ROOT + path + "/deadline",
            json={"deadline": f"2030-01-0{day}T12:00:00Z", "expected_revision": 2},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(competing, (4, 5)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    for r in responses:
        check(
            r,
            r.status_code,
            "concurrent " + str(r.status_code),
            report,
            "ACTIVITY_DEADLINE_CONFLICT" if r.status_code == 409 else None,
        )
    final = request(a, "GET", path, 200, "after concurrency")
    assert final["deadline_revision"] == 3 and final["original_deadline"] == original
    events = request(
        a, "GET", path + "/deadline-history", 200, "history after concurrency"
    )["items"]
    assert len(events) == 3 and events[-1]["new_deadline"] == final["deadline"]
    report["deadline_events"] = events
    report["original_deadline"] = original
    request(
        a,
        "PATCH",
        path + "/status",
        200,
        "complete",
        json={"status": "completed", "expected_status": "in_progress"},
    )
    request(
        a,
        "PATCH",
        path + "/status",
        409,
        "terminal transition conflict",
        "ACTIVITY_TRANSITION_CONFLICT",
        json={"status": "in_progress", "expected_status": "completed"},
    )
    request(
        a,
        "PATCH",
        path + "/status",
        200,
        "reopen",
        json={"status": "pending", "expected_status": "completed"},
    )
    for payload, label in (
        ({**data, "title": "x" * 51}, "title bound"),
        ({**data, "estimated_duration": 9}, "duration bound"),
        ({**data, "deadline": "2030-01-01"}, "timezone required"),
        ({**data, "user_id": 123}, "owner field forbidden"),
    ):
        request(a, "POST", "", 422, label, "VALIDATION_ERROR", json=payload)
    request(
        a,
        "GET",
        "",
        422,
        "reversed deadline range",
        "VALIDATION_ERROR",
        params={
            "deadline_from": "2031-01-01T00:00:00Z",
            "deadline_to": "2030-01-01T00:00:00Z",
        },
    )
    missing = request(
        b, "GET", "/2147483647", 404, "missing activity", "ACTIVITY_NOT_FOUND"
    )
    for method, suffix, kwargs in (
        ("GET", "", {}),
        ("GET", "/deadline-history", {}),
        ("PUT", "", {"json": data}),
        (
            "PATCH",
            "/status",
            {"json": {"status": "pending", "expected_status": "pending"}},
        ),
        (
            "PATCH",
            "/deadline",
            {"json": {"deadline": data["deadline"], "expected_revision": 3}},
        ),
        ("DELETE", "?confirm=true", {}),
    ):
        assert (
            request(
                b,
                method,
                path + suffix,
                404,
                "ownership " + method + suffix,
                "ACTIVITY_NOT_FOUND",
                **kwargs,
            )
            == missing
        )
    assert request(b, "GET", "", 200, "isolated list")["items"] == []
    request(b, "POST", "", 404, "foreign subject", "SUBJECT_NOT_FOUND", json=data)
    request(
        a,
        "POST",
        "",
        404,
        "missing subject",
        "SUBJECT_NOT_FOUND",
        json={**data, "subject_id": 2147483647},
    )
    request(
        a,
        "DELETE",
        path + "?confirm=true",
        409,
        "history blocks delete",
        "ACTIVITY_HAS_DEPENDENCIES",
    )
    check(
        a.delete(f"/api/v1/subjects/{subjects[0]}?confirm=true"),
        409,
        "subject dependency",
        report,
        "SUBJECT_HAS_DEPENDENCIES",
    )
    fresh = request(
        a, "POST", "", 201, "create deletable", json={**data, "title": "Delete smoke"}
    )
    fresh_path = f"/{fresh['id']}"
    report["deleted_activity_id"] = fresh["id"]
    request(a, "DELETE", fresh_path, 422, "delete confirmation", "VALIDATION_ERROR")
    request(a, "DELETE", fresh_path + "?confirm=true", 204, "delete without history")
    request(a, "GET", fresh_path, 404, "deleted absent", "ACTIVITY_NOT_FOUND")
    request(
        a,
        "DELETE",
        fresh_path + "?confirm=true",
        404,
        "second delete",
        "ACTIVITY_NOT_FOUND",
    )
    assert [
        r["id"] for r in request(a, "GET", "", 200, "deleted absent from list")["items"]
    ] == [aid]
    # Retain immutable evidence; leave only cancelled activity and archived subjects.
    retained = request(
        a,
        "PATCH",
        path + "/status",
        200,
        "retain cancelled",
        json={"status": "cancelled", "expected_status": "pending"},
    )
    for client, sid in zip((a, b), subjects):
        check(
            client.post(f"/api/v1/subjects/{sid}/archive"),
            200,
            "archive synthetic subject " + str(sid),
            report,
        )
    assert request(a, "GET", path, 200, "archive preserved activity") == retained
    report["history_preserved"] = True


def logout(client, label, report):
    if client.cookies.get("cognova_refresh"):
        check(
            client.post("/api/v1/auth/logout"),
            403,
            label + " csrf logout rejected",
            report,
            "CSRF_VALIDATION_FAILED",
        )
        check(
            client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": client.cookies.get("cognova_csrf", "")},
            ),
            204,
            label + " logout",
            report,
        )
        check(
            client.get("/api/v1/auth/me"),
            401,
            label + " revoked access",
            report,
            "SESSION_REVOKED",
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("origin")
    parser.add_argument("--frontend-origin", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    url = urlsplit(args.origin)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.path
        or url.query
        or url.fragment
    ):
        raise SystemExit("Use an HTTPS origin without path/query/fragment")
    report = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "checks": {}}
    clients = [
        httpx.Client(
            base_url=args.origin,
            timeout=90,
            headers={"Origin": args.frontend_origin},
            follow_redirects=False,
        )
        for _ in range(2)
    ]
    try:
        a, b = clients
        check(a.get("/api/v1/ready"), 200, "readiness", report)
        check(a.get(ROOT), 401, "without bearer", report)
        spec = a.get("/openapi.json")
        assert (
            spec.status_code == 200
            and ROOT + "/{activity_id}/deadline-history" in spec.json()["paths"]
        )
        report["synthetic_user_ids"] = [
            register(a, "A", report),
            register(b, "B", report),
        ]
        activities(a, b, report)
        check(a.get("/api/v1/ready"), 200, "post-smoke readiness", report)
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["failure_type"] = type(error).__name__
        if type(error) is RuntimeError:
            report["failed_check"] = str(error)
    finally:
        for label, client in zip(("A", "B"), clients):
            try:
                logout(client, label, report)
            except Exception as error:
                report["status"] = "failed"
                report[label + " cleanup_failure"] = type(error).__name__
            client.close()
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        args.evidence.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    k: v
                    for k, v in report.items()
                    if k not in ("checks", "deadline_events")
                }
            )
        )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
