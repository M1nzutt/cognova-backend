from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app.tests.integration.test_activities import setup_activity
from app.tests.integration.test_onboarding import authenticate
from app.tests.integration.test_study_plans import create_study_plan

PLANS = "/api/v1/study-plans"


def challenge_body(**overrides):
    value = {
        "subject_id": None,
        "activity_id": None,
        "study_session_id": None,
        "title": "Resolver cinco ejercicios",
        "description": "Practicar problemas del próximo parcial.",
        "target_type": "custom",
        "target_value": {"evidence": "quiz"},
        "start_at": None,
        "deadline": "2030-01-08T00:00:00Z",
        "generation_criteria": {"rationale": "Preparación del parcial"},
        "depends_on_activity_ids": [],
    }
    value.update(overrides)
    return value


def setup_plan_with_activities(client, registration):
    _, headers, payload, first_activity = setup_activity(client, registration)
    second_activity = client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            **payload,
            "title": "Guía complementaria",
            "deadline": "2030-01-05T12:00:00Z",
        },
    )
    assert second_activity.status_code == 201
    plan = create_study_plan(
        client,
        headers,
        subject_ids=[payload["subject_id"]],
        activity_ids=[first_activity["id"], second_activity.json()["id"]],
    )
    return headers, plan, payload["subject_id"], first_activity, second_activity.json()


def test_challenge_targets_are_structured_contextual_and_plan_scoped(
    client, registration
):
    headers, plan, subject_id, first_activity, second_activity = (
        setup_plan_with_activities(client, registration)
    )
    base = f"{PLANS}/{plan['id']}/challenges"

    activity_challenge = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            activity_id=first_activity["id"],
            target_type="activity_completion",
            target_value={"status": "completed"},
            depends_on_activity_ids=[second_activity["id"]],
        ),
    )
    assert activity_challenge.status_code == 201, activity_challenge.text
    created = activity_challenge.json()
    assert created["source"] == "manual"
    assert created["status"] == "pending"
    assert created["generation_criteria"]["depends_on_activity_ids"] == [
        second_activity["id"]
    ]
    assert "user_id" not in created
    assert activity_challenge.headers["cache-control"] == "no-store"

    minute_challenge = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            target_type="study_minutes",
            target_value={"minutes": 60},
        ),
    )
    assert minute_challenge.status_code == 201
    mastery_challenge = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            target_type="subject_mastery",
            target_value={"criterion": "resolver sin apuntes", "threshold": 80},
        ),
    )
    assert mastery_challenge.status_code == 201
    custom_challenge = client.post(
        base,
        headers=headers,
        json=challenge_body(subject_id=None),
    )
    assert custom_challenge.status_code == 201

    listing = client.get(base, headers=headers, params={"limit": 2})
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 2
    assert listing.json()["next_after_id"] == minute_challenge.json()["id"]
    page = client.get(
        base,
        headers=headers,
        params={"limit": 2, "after_id": listing.json()["next_after_id"]},
    )
    assert len(page.json()["items"]) == 2
    assert page.json()["next_after_id"] is None

    projected = client.get(f"{PLANS}/{plan['id']}", headers=headers)
    assert projected.json()["challenge_count"] == 4
    assert projected.json()["activity_dependency_order"] == [
        second_activity["id"],
        first_activity["id"],
    ]


def test_challenge_state_transitions_edits_and_cycle_validation(client, registration):
    headers, plan, subject_id, first_activity, second_activity = (
        setup_plan_with_activities(client, registration)
    )
    base = f"{PLANS}/{plan['id']}/challenges"
    body = challenge_body(
        subject_id=subject_id,
        activity_id=first_activity["id"],
        target_type="activity_completion",
        target_value={"status": "completed"},
        depends_on_activity_ids=[second_activity["id"]],
    )
    created = client.post(base, headers=headers, json=body)
    assert created.status_code == 201, created.text
    challenge_id = created.json()["id"]
    path = f"{base}/{challenge_id}"

    update = client.put(
        path,
        headers=headers,
        json={**body, "title": "Resolver seis ejercicios"},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "Resolver seis ejercicios"
    cycle = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            activity_id=second_activity["id"],
            target_type="activity_completion",
            target_value={"status": "completed"},
            depends_on_activity_ids=[first_activity["id"]],
        ),
    )
    assert cycle.status_code == 409
    assert cycle.json()["error"]["code"] == "STUDY_PLAN_DEPENDENCY_CONFLICT"

    started = client.post(path + "/start", headers=headers)
    assert started.status_code == 200 and started.json()["status"] == "in_progress"
    immutable = client.put(path, headers=headers, json=body)
    assert immutable.status_code == 409
    completed = client.post(path + "/complete", headers=headers)
    assert completed.status_code == 200 and completed.json()["status"] == "completed"
    repeated = client.post(path + "/fail", headers=headers)
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "STUDY_CHALLENGE_STATE_CONFLICT"

    pending = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            target_type="study_minutes",
            target_value={"minutes": 25},
        ),
    ).json()
    cancelled = client.post(f"{base}/{pending['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"


def test_challenge_ownership_targets_and_onboarding_errors(client, registration):
    headers, plan, subject_id, activity, _ = setup_plan_with_activities(
        client, registration
    )
    other_registration = {**registration, "email": "other-challenge@example.com"}
    _, other_headers, other_payload, other_activity = setup_activity(
        client, other_registration
    )
    base = f"{PLANS}/{plan['id']}/challenges"

    foreign = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            activity_id=other_activity["id"],
            target_type="activity_completion",
            target_value={"status": "completed"},
        ),
    )
    assert foreign.status_code == 409
    assert foreign.json()["error"]["code"] == "STUDY_PLAN_RESOURCE_CONFLICT"
    invalid_target = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            activity_id=activity["id"],
            target_type="activity_completion",
            target_value={"status": "pending"},
        ),
    )
    assert invalid_target.status_code == 422
    assert client.get(base, headers=other_headers).status_code == 404
    assert other_payload["subject_id"] != subject_id

    _, incomplete_headers = authenticate(
        client, {**registration, "email": "incomplete-challenge@example.com"}
    )
    assert client.get(PLANS, headers=incomplete_headers).status_code == 403


def test_concurrent_challenge_start_is_serialized_by_user_lock(client, registration):
    headers, plan, subject_id, activity, _ = setup_plan_with_activities(
        client, registration
    )
    base = f"{PLANS}/{plan['id']}/challenges"
    challenge = client.post(
        base,
        headers=headers,
        json=challenge_body(
            subject_id=subject_id,
            activity_id=activity["id"],
            target_type="activity_completion",
            target_value={"status": "completed"},
        ),
    ).json()
    barrier = Barrier(2)

    def start():
        barrier.wait(timeout=5)
        return client.post(f"{base}/{challenge['id']}/start", headers=headers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: start(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 409]
    final = client.get(f"{base}/{challenge['id']}", headers=headers)
    assert final.status_code == 200
    assert final.json()["status"] == "in_progress"
