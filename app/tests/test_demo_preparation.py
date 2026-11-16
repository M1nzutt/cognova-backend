import json
import os
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.schemas.activity_write import ActivityWrite
from app.schemas.study_session_write import StudySessionWrite
from scripts.demo_scenario import IDENTITY, SUBJECTS, activities, sessions
from scripts.demo_support import (
    Api,
    DemoError,
    Journal,
    credentials,
    secure_directory,
    validate_origin,
)
from scripts.prepare_demo import Preparation


def test_six_week_scenario_uses_valid_public_contracts():
    reference = date(2030, 6, 3)
    assert len(SUBJECTS) == 5
    assert len(activities(reference)) == 30
    assert len(sessions(reference)) == 36
    for row in activities(reference):
        ActivityWrite(**row["body"], subject_id=1)
    for row in sessions(reference):
        StudySessionWrite(**row["body"], subject_id=1, activity_id=1)
    assert len(IDENTITY["name"]) <= 30 and len(IDENTITY["email"]) <= 50
    assert len({row["key"] for row in activities(reference)}) == 30
    assert len({row["key"] for row in sessions(reference)}) == 36


def test_reference_changes_plans_not_actual_execution():
    old = activities(date(2030, 6, 3))
    new = activities(date(2030, 6, 10))
    assert old[0]["body"]["deadline"] != new[0]["body"]["deadline"]
    for item in sessions(date(2030, 6, 3)):
        assert set(item["body"]) == {"planned_start_at", "planned_duration"}


@pytest.mark.parametrize("base", [
    "http://example.com", "https://user:secret@example.com",
    "https://example.com?key=secret", "https://example.com/other",
])
def test_insecure_or_credential_bearing_origin_rejected(base):
    with pytest.raises(DemoError):
        validate_origin(base)


def test_origin_allows_vps_https_and_local_loopback():
    assert validate_origin("https://demo.example.com/") == "https://demo.example.com"
    assert validate_origin("http://127.0.0.1:8080") == "http://127.0.0.1:8080"


def test_journal_prevents_wrong_installation_and_reference(tmp_path):
    Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    with pytest.raises(DemoError):
        Journal(tmp_path, "https://demo.example.com", "2030-06-03")
    with pytest.raises(DemoError):
        Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-10")


def test_uncertain_create_is_not_retried(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.begin("subject-req")
    api = SimpleNamespace(items=lambda _: [], request=Mock())
    task = Preparation(api, journal)
    with pytest.raises(DemoError):
        task.ensure("subject-req", "subjects", {"name": "Demo"}, lambda _: True)
    api.request.assert_not_called()


def test_lost_create_receipt_is_reconciled_without_duplication(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.begin("subject-req")
    api = SimpleNamespace(items=lambda _: [{"id": 42}], request=Mock())
    task = Preparation(api, journal)
    assert task.ensure("subject-req", "subjects", {}, lambda _: True)["id"] == 42
    api.request.assert_not_called()
    assert journal.completed("subject-req")


def test_finished_steps_are_noops_on_repeated_preparation(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.done("decide-ai-initial")
    api = SimpleNamespace(request=Mock())
    Preparation(api, journal).once(
        "decide-ai-initial", "POST", "study-plans/1/accept"
    )
    api.request.assert_not_called()


def test_exhausted_provider_budget_never_generates(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.data["ai_attempts"] = [{"key": "old-1"}, {"key": "old-2"}]
    api = SimpleNamespace(request=Mock())
    with pytest.raises(DemoError):
        Preparation(api, journal).ai_proposal("ai-initial", "accept")
    api.request.assert_not_called()


def test_failed_provider_attempt_is_debited_and_never_automatically_retried(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    api = SimpleNamespace(
        items=lambda _: [],
        request=Mock(side_effect=DemoError("HTTP 503 at POST study-plans/generate")),
    )
    for _ in range(2):
        with pytest.raises(DemoError):
            Preparation(api, journal).ai_proposal("ai-initial", "accept")
    assert api.request.call_count == 1
    assert len(journal.data["ai_attempts"]) == 1
    assert journal.data["ai_attempts"][0]["state"] == "failed_or_uncertain"


def test_credentials_are_stable_and_os_protected(tmp_path):
    secure_directory(tmp_path)
    first = credentials(tmp_path, create=True)
    second = credentials(tmp_path)
    assert first == second
    assert 8 <= len(first["password"]) <= 12
    if os.name == "nt":
        content = (tmp_path / "credentials.dpapi").read_text()
        assert first["password"] not in content
        assert first["email"] not in content
    else:
        assert (tmp_path / "credentials.json").stat().st_mode & 0o077 == 0


def test_journal_contains_no_private_auth_fields(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.done("subject-req", 42)
    content = json.dumps(journal.data)
    assert "password" not in content and "access_token" not in content


def test_completed_timers_are_never_started_again(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    for key, _, _ in SUBJECTS:
        journal.done("measured-" + key)
    api = SimpleNamespace(request=Mock())
    Preparation(api, journal).timers()
    api.request.assert_not_called()


def test_explicit_failed_attempt_retry_is_debited_and_not_repeated(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.data["ai_attempts"] = [{
        "key": "ai-initial", "before_ids": [], "state": "failed_or_uncertain",
        "confirmed_http_failure": True,
    }]
    journal.data["ai_budget"] = 3

    def request(method, path, body=None):
        if path == "study-plans/generate":
            return {"plan": {"id": 42}}
        if path == "study-plans/42":
            return {"ai_proposal_snapshot": {"model": "gemini-3.5-flash-lite"}}
        return {}

    api = SimpleNamespace(items=lambda _: [], request=Mock(side_effect=request))
    task = Preparation(api, journal, retry_failed_ai=True)
    task.ai_proposal("ai-initial", "reject")
    task.ai_proposal("ai-initial", "reject")
    assert len(journal.data["ai_attempts"]) == 2
    assert sum(
        call.args[1] == "study-plans/generate"
        for call in api.request.call_args_list
    ) == 1


def test_pagination_keeps_existing_filters_and_collects_all_resources():
    api = Api("http://127.0.0.1:8080", {})
    api.request = Mock(side_effect=[
        {"items": [{"id": 1}], "next_after_id": 1},
        {"items": [{"id": 2}], "next_after_id": None},
    ])
    assert [row["id"] for row in api.items("subjects?status=all")] == [1, 2]
    assert "status=all" in api.request.call_args.args[1]
    assert "after_id=1" in api.request.call_args.args[1]


def test_recovery_preserves_interrupted_session_and_creates_one_replacement(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    for key, identifier in (
        ("rehearsal-bd", 55), ("subject-bd", 5), ("activity-bd-w6", 30)
    ):
        journal.done(key, identifier)

    def request(method, path, body=None):
        if path == "sessions/55":
            return {"id": 55, "execution_state": "running"}
        if path == "sessions/55/finish":
            assert body["status"] == "cancelled"
            return {"id": 55, "execution_state": "finished",
                    "status": "cancelled", "actual_duration": "50000"}
        if path == "sessions" and method == "POST":
            assert set(body) == {
                "subject_id", "activity_id", "planned_start_at", "planned_duration"
            }
            return {"id": 59}
        raise AssertionError("Unexpected request")

    api = SimpleNamespace(items=lambda _: [], request=Mock(side_effect=request))
    task = Preparation(api, journal)
    task.recover_timer("bd")
    assert journal.data["steps"]["interrupted-rehearsal-bd"]["id"] == 55
    assert journal.data["steps"]["rehearsal-bd"]["id"] == 59
    assert journal.data["recovery_incidents"][0]["seconds"] == "50000"
    assert all(call.args[0] != "DELETE" for call in api.request.call_args_list)


def test_unrelated_later_ai_plan_is_never_adopted(tmp_path):
    journal = Journal(tmp_path, "http://127.0.0.1:8080", "2030-06-03")
    journal.data["ai_attempts"] = [{
        "key": "ai-initial", "before_ids": [], "state": "failed_or_uncertain",
    }]
    api = SimpleNamespace(
        items=Mock(return_value=[{"id": 99, "source": "ai"}]),
        request=Mock(),
    )
    with pytest.raises(DemoError):
        Preparation(api, journal).ai_proposal("ai-initial", "accept")
    api.request.assert_not_called()
