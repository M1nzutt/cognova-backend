"""Permanent demo via public HTTP APIs only. No database access or deletion."""

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.demo_scenario import SUBJECTS, activities, instant, sessions
from scripts.demo_support import (
    Api,
    DemoError,
    Journal,
    credentials,
    private_write,
    secure_directory,
    validate_origin,
)


class Preparation:
    def __init__(self, api: Api, journal: Journal, *, retry_failed_ai=False):
        self.api, self.journal = api, journal
        self.retry_failed_ai = retry_failed_ai
        self.reference = date.fromisoformat(journal.data["reference"])
        self.ids = {
            key: entry["id"] for key, entry in journal.data["steps"].items()
            if entry["state"] == "done" and entry.get("id") is not None
        }

    def ensure(self, key: str, path: str, body: dict, matches):
        if key in self.ids:
            return self.api.request("GET", f"{path}/{self.ids[key]}")
        candidates = [item for item in self.api.items(path) if matches(item)]
        if len(candidates) > 1:
            raise DemoError(
                f"Ambiguous demo resource {key}; nothing will be duplicated"
            )
        if candidates:
            item = candidates[0]
        else:
            self.journal.begin(key)  # Uncertain POSTs are never blindly retried.
            item = self.api.request("POST", path, body)
        self.journal.done(key, item["id"])
        self.ids[key] = item["id"]
        return item

    def once(self, key: str, method: str, path: str, body=None):
        if self.journal.completed(key):
            return
        self.journal.begin(key)
        self.api.request(method, path, body)
        self.journal.done(key)

    def prepare(self, allow_ai: bool):
        self.once("academic-profile", "PUT", "onboarding/academic-profile", {
            "degree_program": "Ingeniería de Software (demostración ficticia)",
            "semester": 5,
        })
        if not self.journal.completed("questionnaire"):
            catalog = self.api.request("GET", "questionnaire/catalog")
            answers = {}
            for index, question in enumerate(catalog["questions"]):
                options = [option["id"] for option in question["options"]
                           if option["id"] != "other"]
                answers[question["id"]] = {
                    "choices": [options[index % len(options)]], "other_text": None,
                }
            self.once("questionnaire", "POST", "questionnaire", {
                "questionnaire_version": catalog["questionnaire_version"],
                "answers": answers,
            })
        palette = self.api.request("GET", "subjects/catalog")
        for index, (key, name, difficulty) in enumerate(SUBJECTS):
            self.ensure(f"subject-{key}", "subjects", {
                "name": name, "difficulty": difficulty, "status": "active",
                "color_base": palette["color_bases"][index],
                "color_shade": palette["color_shades"][1],
            }, lambda row, name=name: row["name"] == name)
        for item in activities(self.reference):
            body = {
                **item["body"],
                "subject_id": self.ids["subject-" + item["subject_key"]],
            }
            record = self.ensure(
                item["key"], "activities", body,
                lambda row, body=body: row["title"] == body["title"]
                and row["subject_id"] == body["subject_id"],
            )
            if item["week"] < 2:
                self.once("complete-" + item["key"], "PATCH",
                          f"activities/{record['id']}/status",
                          {"expected_status": "pending", "status": "completed"})
            elif item["week"] == 3:
                self.once("progress-" + item["key"], "PATCH",
                          f"activities/{record['id']}/status",
                          {"expected_status": "pending", "status": "in_progress"})
            if item["key"] in {"activity-req-w3", "activity-arq-w4"}:
                current = self.api.request("GET", f"activities/{record['id']}")
                self.once("priority-" + item["key"], "PUT",
                          f"activities/{record['id']}",
                          {**body, "status": current["status"],
                           "deadline": current["deadline"], "priority": "high"})
            if item["key"] in {"activity-req-w3", "activity-bd-w4", "activity-qa-w5"}:
                self.once("postpone-" + item["key"], "PATCH",
                          f"activities/{record['id']}/deadline",
                          {"deadline": (
                              datetime.fromisoformat(body["deadline"])
                              + timedelta(days=3)
                          ).isoformat(), "expected_revision": 0})
        for item in sessions(self.reference):
            body = {
                **item["body"],
                "subject_id": self.ids["subject-" + item["subject_key"]],
                "activity_id": self.ids[item["activity_key"]],
            }
            record = self.ensure(item["key"], "sessions", body, lambda row, body=body:
                row["subject_id"] == body["subject_id"]
                and row["activity_id"] == body["activity_id"]
                and datetime.fromisoformat(
                    row["planned_start_at"].replace("Z", "+00:00"))
                == datetime.fromisoformat(body["planned_start_at"]))
            if item["key"] in {"session-req-w1", "session-arq-w1"}:
                status = "postponed" if item["key"] == "session-req-w1" else "cancelled"
                self.once("outcome-" + item["key"], "POST",
                          f"sessions/{record['id']}/finish",
                          {"status": status, "context": None, "other_text": None})
        self.manual_plans()
        if allow_ai:
            self.ai_proposal("ai-initial", "accept")

    def plan_body(self, name: str, *, foundation=False):
        chosen = activities(self.reference)
        return {
            "name": name,
            "objective": (
                "TurnoClaro: sistema ficticio de reservas. Las fechas pasadas son "
                "planificación; ejecución y decisiones conservan la fecha real."
            ),
            "start_at": instant(self.reference, -37, 0),
            "end_at": instant(self.reference, 9, 23),
            "subject_ids": [self.ids["subject-" + key] for key, _, _ in SUBJECTS],
            "activity_ids": [self.ids[item["key"]] for item in chosen
                             if not foundation or item["week"] < 2],
            "study_session_ids": [] if foundation else [
                self.ids[item["key"]] for item in sessions(self.reference)
            ],
        }

    def manual_plans(self):
        for key, name, foundation in (
            ("manual-foundations", "TurnoClaro · Fundamentos", True),
            ("manual-route", "TurnoClaro · Ruta del semestre", False),
        ):
            self.ensure(key, "study-plans", self.plan_body(name, foundation=foundation),
                        lambda row, name=name: row["name"] == name)
            if foundation:
                self.once("activate-" + key, "POST",
                          f"study-plans/{self.ids[key]}/activate")
                self.once("finish-" + key, "POST",
                          f"study-plans/{self.ids[key]}/complete")
        plan_id = self.ids["manual-route"]
        edited = self.plan_body("TurnoClaro · Ruta revisada")
        self.once("edit-manual-route", "PUT", f"study-plans/{plan_id}", edited)
        self.once("activate-manual-route", "POST", f"study-plans/{plan_id}/activate")
        challenges = [
            ("req", 1, "Entrevistas revisadas", "completed"),
            ("bd", 2, "Normalización comprobada", "completed"),
            ("qa", 3, "Pruebas pospuestas", "failed"),
            ("arq", 4, "Contrato en revisión", "in_progress"),
            ("req", 4, "Validar prototipo", "pending"),
            ("agil", 6, "Preparar sustentación", "pending"),
        ]
        for index, (subject, week, title, status) in enumerate(challenges):
            activity_id = self.ids[f"activity-{subject}-w{week}"]
            item = self.ensure(f"challenge-{index}",
                               f"study-plans/{plan_id}/challenges", {
                "title": title,
                "description": "Revisar la entrega TurnoClaro y su resultado.",
                "subject_id": self.ids["subject-" + subject],
                "activity_id": activity_id,
                "study_session_id": None, "target_type": "activity_completion",
                "target_value": {"status": "completed"},
                "start_at": None, "deadline": instant(self.reference, 6, 22),
                "generation_criteria": {
                    "origin": "manual_demo",
                    "evidence": "Actividad del semestre ficticio TurnoClaro.",
                },
                "depends_on_activity_ids": (
                    [self.ids["activity-req-w3"]] if index == 4 else []
                ),
            }, lambda row, title=title: row["title"] == title)
            path = f"study-plans/{plan_id}/challenges/{item['id']}"
            if status != "pending":
                self.once(f"start-challenge-{index}", "POST", path + "/start")
            if status in {"completed", "failed"}:
                self.once(f"end-challenge-{index}", "POST",
                          path + ("/complete" if status == "completed" else "/fail"))

    def ai_proposal(self, key: str, decision: str):
        if key not in self.ids:
            attempts = self.journal.data["ai_attempts"]
            prior = [entry for entry in attempts if entry["key"] == key]
            if prior:
                # A new AI plan in the list might belong to a later UI action.
                # Only an exact persisted receipt is safe to adopt automatically.
                receipts = [entry for entry in prior if entry.get("plan_id")
                            and entry["state"] == "succeeded"]
                if receipts:
                    item = self.api.request(
                        "GET", f"study-plans/{receipts[-1]['plan_id']}"
                    )
                elif self.retry_failed_ai and prior[-1].get("confirmed_http_failure"):
                    item = self._generate_ai(key)
                else:
                    raise DemoError(
                        "Previous AI attempt uncertain/failed; no automatic retry"
                    )
            else:
                item = self._generate_ai(key)
            self.ids[key] = item["id"]
            self.journal.done(key, item["id"])
        plan_id = self.ids[key]
        detail = self.api.request("GET", f"study-plans/{plan_id}")
        if not detail.get("ai_proposal_snapshot"):
            raise DemoError("Real AI proposal has no persisted snapshot")
        if decision == "accept":
            self.once("edit-" + key, "PUT", f"study-plans/{plan_id}", {
                "name": "TurnoClaro · Propuesta elegida",
                "objective": detail["objective"],
                "start_at": detail["start_at"], "end_at": detail["end_at"],
                "subject_ids": [row["id"] for row in detail["subjects"]],
                "activity_ids": [row["id"] for row in detail["activities"]],
                "study_session_ids": [row["id"] for row in detail["study_sessions"]],
            })
        self.once("decide-" + key, "POST", f"study-plans/{plan_id}/{decision}")

    def _generate_ai(self, key: str):
        attempts = self.journal.data["ai_attempts"]
        if len(attempts) >= self.journal.data.get("ai_budget", 2):
            raise DemoError("Explicit provider budget exhausted")
        attempts.append({
            "key": key, "at": datetime.now(timezone.utc).isoformat(),
            "before_ids": [row["id"] for row in self.api.items("study-plans")],
            "state": "started",
        })
        self.journal.save()  # Debit BEFORE sending, including failed requests.
        try:
            result = self.api.request("POST", "study-plans/generate")
        except DemoError as error:
            attempts[-1].update(
                state="failed_or_uncertain",
                confirmed_http_failure=str(error).startswith("HTTP "),
            )
            self.journal.save()
            raise
        item = result["plan"]
        attempts[-1].update(state="succeeded", plan_id=item["id"])
        self.journal.save()
        return item

    def timers(self):
        for index, (key, _, _) in enumerate(SUBJECTS):
            step = "measured-" + key
            if self.journal.completed(step):
                continue
            session_id = self.ids["rehearsal-" + key]
            record = self.api.request("GET", f"sessions/{session_id}")
            target_seconds = 600 if index == 0 else 60
            if record["execution_state"] == "planned":
                record = self.api.request("POST", f"sessions/{session_id}/start")
                print(f"TIMER_STARTED={key};REAL_SECONDS={target_seconds}", flush=True)
            if record["execution_state"] == "finished":
                self.check_intervals(record)
                self.journal.done(step)
                continue
            if record["execution_state"] == "paused":
                record = self.api.request("POST", f"sessions/{session_id}/resume")
            closed = sum(
                (
                    datetime.fromisoformat(row["ended_at"].replace("Z", "+00:00"))
                    - datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
                ).total_seconds()
                for row in record["intervals"] if row["ended_at"] is not None
            )
            # Genuine wall time, not a fake clock or a supplied duration.
            open_interval = next(
                row for row in record["intervals"] if row["ended_at"] is None
            )
            elapsed_open = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(
                    open_interval["started_at"].replace("Z", "+00:00"))
            ).total_seconds()
            time.sleep(max(0, target_seconds - closed - elapsed_open) + 0.1)
            if index == 1:
                self.api.request("POST", f"sessions/{session_id}/pause")
                self.api.request("POST", f"sessions/{session_id}/resume")
            record = self.api.request("POST", f"sessions/{session_id}/finish", {
                "status": "completed" if index == 0 else "partial",
                "context": "finished_early" if index == 0 else "interrupted",
                "other_text": None,
            })
            self.check_intervals(record)
            self.journal.done(step)

    def recover_timer(self, subject_key: str):
        """Explicit recovery, never erase or shorten the interrupted interval."""
        if subject_key not in {key for key, _, _ in SUBJECTS}:
            raise DemoError("Unknown rehearsal subject")
        recovery_key = "recovery-session-" + subject_key
        original_key = "interrupted-rehearsal-" + subject_key
        original_id = self.ids.get(original_key, self.ids["rehearsal-" + subject_key])
        row = self.api.request("GET", f"sessions/{original_id}")
        if row["execution_state"] in {"running", "paused"}:
            row = self.api.request("POST", f"sessions/{original_id}/finish", {
                "status": "cancelled", "context": "other",
                "other_text": (
                    "Interrupción técnica durante la preparación de la demo. "
                    "El temporizador permaneció abierto; "
                    "no representa estudio efectivo."
                ),
            })
        elif row["status"] != "cancelled":
            raise DemoError("Recovery only applies to interrupted/cancelled rehearsal")
        self.journal.done(original_key, original_id)
        incidents = self.journal.data.setdefault("recovery_incidents", [])
        if not any(item["session_id"] == original_id for item in incidents):
            incidents.append({
                "session_id": original_id,
                "seconds": row["actual_duration"],
                "reason": "server_restart_left_timer_open_not_study",
            })
            self.journal.save()
        body = {
            "subject_id": self.ids["subject-" + subject_key],
            "activity_id": self.ids[f"activity-{subject_key}-w6"],
            "planned_start_at": instant(self.reference, 1, 14),
            "planned_duration": 10,
        }
        replacement = self.ensure(
            recovery_key, "sessions", body,
            lambda item: item["subject_id"] == body["subject_id"]
            and item["activity_id"] == body["activity_id"]
            and datetime.fromisoformat(
                item["planned_start_at"].replace("Z", "+00:00"))
            == datetime.fromisoformat(body["planned_start_at"]),
        )
        self.journal.done("rehearsal-" + subject_key, replacement["id"])
        self.ids["rehearsal-" + subject_key] = replacement["id"]
        # The manual plan is already active and cannot be edited legitimately.
        # The new session remains owned and linked to its semester activity;
        # a future draft may select it without rewriting the accepted plan.

    @staticmethod
    def check_intervals(record):
        elapsed = sum(
            (
                datetime.fromisoformat(row["ended_at"].replace("Z", "+00:00"))
                - datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
            ).total_seconds()
            for row in record["intervals"] if row["ended_at"] is not None
        )
        if elapsed <= 0 or abs(elapsed - float(record["actual_duration"])) > 0.01:
            raise DemoError("Timer intervals and real duration disagree")

    def contextual(self, allow_ai: bool):
        if not all(self.journal.completed("measured-" + key) for key, _, _ in SUBJECTS):
            raise DemoError(
                "Five measured sessions required before contextual proposal"
            )
        for key, _, _ in SUBJECTS:
            row = self.api.request("GET", f"sessions/{self.ids['rehearsal-' + key]}")
            if row["status"] not in {"completed", "partial"}:
                raise DemoError("Measured sessions no longer meet analysis eligibility")
            self.check_intervals(row)
        # A real change AFTER accepting the first proposal gives the second
        # proposal new evidence; it is not an unnecessary regeneration.
        if not self.journal.completed("decide-ai-initial"):
            raise DemoError(
                "Accept the initial real proposal before requesting another"
            )
        activity_id = self.ids["activity-req-w6"]
        current = self.api.request("GET", f"activities/{activity_id}")
        self.once("context-priority", "PUT", f"activities/{activity_id}", {
            key: ({"priority": "high",
                   "notes": "TurnoClaro demo: tras cuatro ensayos parciales, "
                            "se prioriza cerrar requisitos antes de ampliar alcance."}
                  .get(key, current[key]))
            for key in (
                "title", "subject_id", "deadline", "priority", "status",
                "estimated_duration", "notes",
            )
        })
        if allow_ai:
            self.ai_proposal("ai-contextual", "reject")
        else:
            raise DemoError("Contextual generation requires explicit --allow-ai")

    def verify(self):
        subjects = self.api.items("subjects?status=all")
        activity_rows = self.api.items("activities")
        session_rows = self.api.items("sessions")
        plans = self.api.items("study-plans")
        subject_ids = {row["id"] for row in subjects}
        activities_by_id = {row["id"]: row for row in activity_rows}
        expected_sessions = 36 + len(self.journal.data.get("recovery_incidents", []))
        if not (len(subjects) >= 5 and len(activity_rows) >= 30
                and len(session_rows) >= expected_sessions):
            raise DemoError("Required demo resources missing; do not overwrite changes")
        for prefix, present in (
            ("activity-", set(activities_by_id)), ("subject-", subject_ids)
        ):
            required = {
                entry["id"] for key, entry in self.journal.data["steps"].items()
                if key.startswith(prefix) and entry["state"] == "done"
                and entry.get("id") is not None
            }
            if not required <= present:
                raise DemoError("A prepared resource was removed; review required")
        for row in session_rows:
            if (
                row["subject_id"] not in subject_ids
                or (row["activity_id"] is not None and
                    activities_by_id[row["activity_id"]]["subject_id"]
                    != row["subject_id"])
            ):
                raise DemoError("Academic relationship mismatch")
            if row["status"] in {"completed", "partial"}:
                self.check_intervals(self.api.request("GET", f"sessions/{row['id']}"))
        details = [self.api.request("GET", f"study-plans/{row['id']}") for row in plans]
        session_ids = {row["id"] for row in session_rows}
        required_sessions = {
            entry["id"] for key, entry in self.journal.data["steps"].items()
            if (key.startswith(("session-", "rehearsal-", "interrupted-rehearsal-"))
                or key == "future-timer")
            and entry["state"] == "done" and entry.get("id") is not None
        }
        if not required_sessions <= session_ids:
            raise DemoError("A prepared session was removed; review required")
        for plan in details:
            if (
                not {row["id"] for row in plan["subjects"]} <= subject_ids
                or not {row["id"] for row in plan["activities"]}
                <= set(activities_by_id)
                or not {row["id"] for row in plan["study_sessions"]} <= session_ids
            ):
                raise DemoError("Plan contains an unrelated academic resource")
        challenges = [
            item for row in plans
            for item in self.api.items(f"study-plans/{row['id']}/challenges")
        ]
        overview = self.api.request("GET", "analytics/overview")
        report = {
            "reference": str(self.reference), "user_id": self.journal.data["user_id"],
            "subjects": len(subjects), "activities": len(activity_rows),
            "sessions": len(session_rows), "plans": len(plans),
            "plan_states": [row["status"] for row in details],
            "challenge_states": sorted({row["status"] for row in challenges}),
            "decisions": [d["action"] for row in details for d in row["decisions"]],
            "snapshots": sum(bool(row.get("ai_proposal_snapshot")) for row in details),
            "deadline_history_events": sum(
                row["deadline_revision"] for row in activity_rows
            ),
            "gemini_attempts": len(self.journal.data["ai_attempts"]),
            "overview": overview,
            "valid_rehearsal_seconds": sum(
                float(row["actual_duration"]) for row in session_rows
                if row["status"] in {"completed", "partial"}
            ),
            "recovery_incidents": self.journal.data.get("recovery_incidents", []),
            "ai_preparation_complete": all(
                self.journal.completed("decide-" + key)
                for key in ("ai-initial", "ai-contextual")
            ),
            "limitations": [
                "Six-week dates are planning, not retroactive execution.",
                "Actual intervals and decisions begin at real preparation time.",
                "Behavior observations are read-only, not persisted by the API.",
            ],
        }
        private_write(self.journal.path.parent / "report.json",
                      json.dumps(report, indent=2).encode())
        print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=[
            "prepare", "timers", "recover-timer", "context", "verify", "credentials"
        ]
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--state-dir", type=Path,
                        default=Path.home() / ".local/state/cognova/demo")
    parser.add_argument("--reference", type=date.fromisoformat)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-ai", action="store_true")
    parser.add_argument("--ai-budget", type=int, choices=range(1, 11),
                        help="Explicit lifetime attempt budget (default 2)")
    parser.add_argument("--retry-failed-ai", action="store_true",
                        help="Explicit operator retry after resolving failed attempt")
    parser.add_argument("--subject-key", choices=[key for key, _, _ in SUBJECTS])
    args = parser.parse_args()
    directory = args.state_dir.resolve()
    if any((parent / ".git").exists() for parent in (directory, *directory.parents)):
        raise DemoError("Private state must live OUTSIDE the repository")
    secure_directory(directory)
    if args.phase == "credentials":
        # Explicit local operator command, never used in logs or Git.
        print(json.dumps(credentials(directory), ensure_ascii=False))
        return
    if args.phase != "verify" and not args.apply:
        raise DemoError("No academic write authorized: use --apply explicitly")
    base = validate_origin(args.base_url)
    existing = directory / "progress.json"
    reference = args.reference or (
        date.fromisoformat(json.loads(existing.read_text())["reference"])
        if existing.exists() else datetime.now(timezone.utc).date()
    )
    lock = directory / "prepare.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise DemoError(
            "Demo preparation already locked; review unfinished run"
        ) from None
    with os.fdopen(fd, "w") as handle:
        json.dump({"pid": os.getpid(), "phase": args.phase,
                   "started_at": datetime.now(timezone.utc).isoformat()}, handle)
    api = None
    try:
        journal = Journal(directory, base, str(reference))
        if args.ai_budget is not None:
            if len(journal.data["ai_attempts"]) > args.ai_budget:
                raise DemoError("Budget cannot be lower than recorded attempts")
            journal.data["ai_budget"] = args.ai_budget
            journal.save()
        api = Api(base, credentials(directory, create=args.phase == "prepare"))
        user = api.login(register=args.phase == "prepare")
        if journal.data["user_id"] not in {None, user["id"]}:
            raise DemoError("Account does not match the saved owner")
        journal.data["user_id"] = user["id"]
        journal.save()
        task = Preparation(api, journal, retry_failed_ai=args.retry_failed_ai)
        if args.phase == "prepare":
            task.prepare(args.allow_ai)
        elif args.phase == "timers":
            task.timers()
        elif args.phase == "recover-timer":
            if not args.subject_key:
                raise DemoError("Recovery requires an explicit --subject-key")
            task.recover_timer(args.subject_key)
        elif args.phase == "context":
            task.contextual(args.allow_ai)
        elif args.phase == "verify":
            task.verify()
    finally:
        if api and api.token:
            try:
                api.logout()
            except DemoError:
                print("AUTH_LOGOUT_NEEDS_REVIEW", file=sys.stderr)
        lock.unlink()


if __name__ == "__main__":
    try:
        main()
    except DemoError as error:
        print("DEMO_STOPPED: " + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print("DEMO_STOPPED: " + type(error).__name__, file=sys.stderr)
        sys.exit(1)
