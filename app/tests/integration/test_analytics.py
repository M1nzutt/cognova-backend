import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_onboarding import authenticate
from app.tests.integration.test_study_challenges import challenge_body
from app.tests.integration.test_study_plans import create_study_plan
from app.tests.integration.test_study_sessions import create_plan as create_session
from app.tests.integration.test_subjects import onboard

BASE = "/api/v1/analytics"
RANGE = {"from": "2030-01-01T00:00:00Z", "to": "2031-01-01T00:00:00Z"}


def get(client, headers, path, **params):
    response = client.get(f"{BASE}/{path}", headers=headers, params=params)
    assert response.headers["cache-control"] == "no-store"
    return response


def test_analytics_requires_auth_and_completed_onboarding(client, registration):
    for path in ("overview", "search"):
        response = client.get(
            f"{BASE}/{path}", params={"prefix": "fis"} if path == "search" else None
        )
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
    _, incomplete = authenticate(client, registration)
    response = get(client, incomplete, "overview")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ONBOARDING_REQUIRED"


def test_study_time_clips_intervals_buckets_and_counts_sessions(
    client, registration, database, monkeypatch
):
    from app.services import study_session_service

    user, headers, activity_body, _ = setup_activity(client, registration)
    subject_id = activity_body["subject_id"]
    now = {"value": datetime(2030, 1, 1, 23, 59, 50, tzinfo=timezone.utc)}
    monkeypatch.setattr(study_session_service, "utc_now", lambda: now["value"])
    session = create_session(client, headers, subject_id)
    path = f"/api/v1/sessions/{session['id']}"
    assert client.post(path + "/start", headers=headers).status_code == 200
    now["value"] += timedelta(seconds=20)
    assert client.post(path + "/pause", headers=headers).status_code == 200

    response = get(
        client,
        headers,
        "study-time",
        **{
            "from": "2030-01-01T23:59:55Z",
            "to": "2030-01-02T00:00:05Z",
            "timezone": "UTC",
            "granularity": "day",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_seconds"] == "10.000000"
    assert payload["total_minutes"] == "0.166667"
    assert payload["sessions_count"] == 1
    assert payload["by_subject"] == [
        {
            "subject_id": subject_id,
            "name": "Matemáticas",
            "seconds": "10.000000",
            "minutes": "0.166667",
            "sessions_count": 1,
        }
    ]
    assert [item["seconds"] for item in payload["buckets"]] == [
        "5.000000",
        "5.000000",
    ]
    with database.session() as db:
        source_seconds = db.execute(
            text(
                "SELECT COALESCE(SUM(EXTRACT(EPOCH FROM "
                "LEAST(i.ended_at, :to_at) - GREATEST(i.started_at, :from_at))), 0) "
                "FROM study_session_intervals AS i "
                "JOIN study_sessions AS s ON s.id = i.session_id "
                "WHERE s.user_id = :user_id AND i.ended_at IS NOT NULL "
                "AND i.started_at < :to_at AND i.ended_at > :from_at"
            ),
            {
                "user_id": user["user"]["id"],
                "from_at": datetime(2030, 1, 1, 23, 59, 55, tzinfo=timezone.utc),
                "to_at": datetime(2030, 1, 2, 0, 0, 5, tzinfo=timezone.utc),
            },
        ).scalar_one()
    assert Decimal(str(source_seconds)) == Decimal(payload["total_seconds"])

    empty = get(
        client,
        headers,
        "study-time",
        **{
            "from": "2030-01-02T00:00:10Z",
            "to": "2030-01-02T00:00:20Z",
            "timezone": "UTC",
        },
    )
    assert empty.status_code == 200
    assert empty.json()["total_seconds"] == "0.000000"
    assert empty.json()["sessions_count"] == 0
    overview = get(client, headers, "overview").json()
    assert overview["total_studied_seconds"] == "20.000000"
    assert overview["finished_sessions"] == 0
    assert overview["pending_activities"] == 1
    assert overview["subjects_with_activity"] == 1


def test_cancelled_timer_is_separate_from_studied_time_and_ai_evidence(
    client, registration, monkeypatch, database
):
    from app.academic_intelligence.academic_context import AcademicContext
    from app.services import study_session_service

    user, headers, activity_data, _ = setup_activity(client, registration)
    clock = {"now": datetime(2030, 1, 1, tzinfo=timezone.utc)}
    monkeypatch.setattr(study_session_service, "utc_now", lambda: clock["now"])

    cancelled = create_session(client, headers, activity_data["subject_id"])
    cancelled_path = f"/api/v1/sessions/{cancelled['id']}"
    assert client.post(cancelled_path + "/start", headers=headers).status_code == 200
    clock["now"] += timedelta(seconds=45662, microseconds=422572)
    result = client.post(
        cancelled_path + "/finish",
        headers=headers,
        json={"status": "cancelled", "context": "interrupted"},
    )
    assert result.status_code == 200
    assert result.json()["actual_duration"] == "45662.422572"

    clock["now"] += timedelta(seconds=1)
    partial = create_session(client, headers, activity_data["subject_id"])
    partial_path = f"/api/v1/sessions/{partial['id']}"
    assert client.post(partial_path + "/start", headers=headers).status_code == 200
    clock["now"] += timedelta(seconds=840, microseconds=735370)
    result = client.post(
        partial_path + "/finish",
        headers=headers,
        json={"status": "partial", "context": "tired"},
    )
    assert result.status_code == 200
    assert result.json()["actual_duration"] == "840.735370"

    overview = get(client, headers, "overview").json()
    assert overview["total_studied_seconds"] == "840.735370"
    assert overview["cancelled_session_seconds"] == "45662.422572"
    assert overview["cancelled_session_minutes"] == "761.040376"

    ranged = get(
        client,
        headers,
        "study-time",
        **{
            "from": "2030-01-01T00:00:00Z",
            "to": "2030-01-03T00:00:00Z",
            "timezone": "UTC",
            "granularity": "day",
        },
    ).json()
    assert ranged["total_seconds"] == "840.735370"
    assert ranged["cancelled_seconds"] == "45662.422572"
    assert ranged["cancelled_minutes"] == "761.040376"
    assert ranged["cancelled_sessions_count"] == 1
    assert ranged["sessions_count"] == 1
    assert sum(float(bucket["seconds"]) for bucket in ranged["buckets"]) == 840.73537
    assert ranged["by_subject"][0]["seconds"] == "840.735370"

    with database.session() as db:
        context = AcademicContext(db, user["user"]["id"])
        evidence = json.loads(context.as_json())
    evidence_by_id = {row["id"]: row for row in evidence["sessions"]}
    assert evidence_by_id[cancelled["id"]]["actual_minutes"] == 0
    assert evidence_by_id[cancelled["id"]]["cancelled_elapsed_minutes"] == (
        45662.422572 / 60
    )
    assert evidence_by_id[partial["id"]]["actual_minutes"] == 840.73537 / 60


def test_study_time_local_day_bucket_respects_dst_transition():
    from zoneinfo import ZoneInfo

    from app.analytics.study_time_service import AnalyticsStudyTimeService

    zone = ZoneInfo("America/New_York")
    ranges = AnalyticsStudyTimeService._buckets(
        datetime(2030, 3, 10, 0, tzinfo=zone),
        datetime(2030, 3, 11, 0, tzinfo=zone),
        "America/New_York",
        "day",
    )
    assert len(ranges) == 1
    start, end = ranges[0]
    assert (
        end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
    ).total_seconds() == 23 * 3600


def test_timeline_mixes_owned_events_paginates_and_never_writes(
    client, registration, database, monkeypatch
):
    from app.services import study_session_service

    event_time = datetime.now(timezone.utc) + timedelta(hours=1)
    timeline_range = {
        "from": (event_time - timedelta(days=1)).isoformat(),
        "to": (event_time + timedelta(days=2)).isoformat(),
    }
    _, headers, activity_body, activity = setup_activity(client, registration)
    plan = create_study_plan(client, headers, subject_ids=[activity_body["subject_id"]])
    edited = client.put(
        f"/api/v1/study-plans/{plan['id']}",
        headers=headers,
        json={
            "name": "Plan actualizado",
            "objective": "Practicar antes del parcial.",
            "start_at": "2030-01-01T00:00:00Z",
            "end_at": "2030-01-10T00:00:00Z",
            "subject_ids": [activity_body["subject_id"]],
            "activity_ids": [],
            "study_session_ids": [],
        },
    )
    assert edited.status_code == 200
    challenge = client.post(
        f"/api/v1/study-plans/{plan['id']}/challenges",
        headers=headers,
        json=challenge_body(subject_id=activity_body["subject_id"]),
    )
    assert challenge.status_code == 201
    deadline = client.patch(
        f"/api/v1/activities/{activity['id']}/deadline",
        headers=headers,
        json={
            "deadline": (event_time + timedelta(days=1)).isoformat(),
            "expected_revision": 0,
        },
    )
    assert deadline.status_code == 200

    from app.tests.integration.test_study_sessions import create_plan as create_session

    now = {"value": event_time}
    monkeypatch.setattr(study_session_service, "utc_now", lambda: now["value"])
    session = create_session(
        client,
        headers,
        activity_body["subject_id"],
        planned_start_at=event_time.isoformat(),
    )
    session_path = f"/api/v1/sessions/{session['id']}"
    assert client.post(session_path + "/start", headers=headers).status_code == 200
    now["value"] += timedelta(seconds=5)
    assert client.post(session_path + "/pause", headers=headers).status_code == 200

    with database.session() as db:
        before = {
            table: db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in (
                "activities",
                "activity_deadline_events",
                "study_sessions",
                "study_session_intervals",
                "study_plans",
                "study_plan_decisions",
                "study_challenges",
            )
        }
    first = get(client, headers, "timeline", **timeline_range, limit=2)
    assert first.status_code == 200, first.text
    pages = first.json()["items"][:]
    while first.json()["next_cursor"]:
        first = get(
            client,
            headers,
            "timeline",
            **timeline_range,
            limit=2,
            cursor=first.json()["next_cursor"],
        )
        assert first.status_code == 200, first.text
        pages.extend(first.json()["items"])
    assert {item["category"] for item in pages} >= {
        "activity",
        "study_session",
        "plan",
        "decision",
        "challenge",
    }
    assert any(item["event_type"] == "deadline_changed" for item in pages)
    assert any(item["event_type"] == "started" for item in pages)
    assert any(item["event_type"] == "ended" for item in pages)
    activity_only = get(
        client, headers, "timeline", **timeline_range, category="activity"
    )
    assert activity_only.status_code == 200
    assert all(item["category"] == "activity" for item in activity_only.json()["items"])
    assert all("user_id" not in item for item in pages)
    category_rank = {
        "activity": 0,
        "study_session": 1,
        "decision": 2,
        "plan": 3,
        "challenge": 4,
    }
    order_keys = []
    for item in pages:
        _, resource_id, occurrence_id, event_type = item["event_id"].split(":", 3)
        order_keys.append(
            (
                datetime.fromisoformat(item["occurred_at"].replace("Z", "+00:00")),
                category_rank[item["category"]],
                int(resource_id),
                int(occurrence_id),
                event_type,
            )
        )
    assert order_keys == sorted(order_keys)
    assert all(
        "proposed_value" not in item["details"]
        and "chosen_value" not in item["details"]
        for item in pages
    )
    cursor = get(client, headers, "timeline", **timeline_range, limit=1).json()[
        "next_cursor"
    ]
    invalid = get(
        client,
        headers,
        "timeline",
        **timeline_range,
        limit=1,
        category="activity",
        cursor=cursor,
    )
    assert invalid.status_code == 422
    with database.session() as db:
        after = {
            table: db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in before
        }
    assert after == before


def test_search_filters_ownership_cursor_and_user_id_rejection(client, registration):
    _, owner, payload, activity = setup_activity(client, registration)
    from app.tests.integration.test_subjects import create as create_subject

    extra_subject = create_subject(client, owner, name="Materia avanzada")
    assert extra_subject.status_code == 201
    _, stranger = onboard(
        client, {**registration, "email": "analytics-other@example.com"}
    )
    owner_results = get(client, owner, "search", prefix="Mat", type="subject", limit=1)
    assert owner_results.status_code == 200
    assert all(item["type"] == "subject" for item in owner_results.json()["items"])
    assert owner_results.json()["next_cursor"] is not None
    second_page = get(
        client,
        owner,
        "search",
        prefix="Mat",
        type="subject",
        limit=1,
        cursor=owner_results.json()["next_cursor"],
    )
    assert second_page.status_code == 200
    assert second_page.json()["next_cursor"] is None
    assert (
        owner_results.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]
    )
    assert (
        get(client, owner, "search", prefix="Fis", type="activity").json()["items"]
        == []
    )
    activity_search = get(
        client, owner, "search", prefix=activity["title"][:3], type="activity"
    )
    assert [item["id"] for item in activity_search.json()["items"]] == [activity["id"]]
    assert get(client, stranger, "search", prefix="Mat").json()["items"] == []
    assert get(client, stranger, "timeline", **RANGE).json()["items"] == []
    invalid = client.get(
        f"{BASE}/search",
        headers=owner,
        params={"prefix": "Fis", "user_id": payload["subject_id"]},
    )
    assert invalid.status_code == 422
    assert invalid.headers["cache-control"] == "no-store"


def test_overview_reports_descriptive_owned_totals(client, registration):
    _, headers, _, _ = setup_activity(client, registration)
    response = get(client, headers, "overview")
    assert response.status_code == 200
    data = response.json()
    assert data["pending_activities"] == 1
    assert data["subjects_with_activity"] == 1
    assert data["total_studied_seconds"] == "0.000000"
    assert "user_id" not in data
