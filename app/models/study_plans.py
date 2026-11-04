"""Persistence mappings for external Database revision 0007.

Database owns the schema. These mappings let the Backend read and write the
release without taking ownership of DDL.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_study_plans_user",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        UniqueConstraint("user_id", "id", name="uq_study_plans_user_id_id"),
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100 AND name = btrim(name) "
            "AND name !~ '^[[:space:]]*$'",
            name="ck_study_plans_name",
        ),
        CheckConstraint(
            "char_length(objective) BETWEEN 1 AND 2000 "
            "AND objective = btrim(objective) "
            "AND objective !~ '^[[:space:]]*$'",
            name="ck_study_plans_objective",
        ),
        CheckConstraint(
            "isfinite(start_at) AND isfinite(end_at) AND end_at > start_at",
            name="ck_study_plans_dates",
        ),
        CheckConstraint(
            "status IN ('draft','active','completed','abandoned')",
            name="ck_study_plans_status",
        ),
        CheckConstraint("source IN ('ai','manual')", name="ck_study_plans_source"),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND updated_at >= created_at",
            name="ck_study_plans_timestamps",
        ),
        Index(
            "ix_study_plans_user_status_start",
            "user_id",
            "status",
            "start_at",
            "id",
        ),
        Index("ix_study_plans_user_end", "user_id", "end_at", "id"),
    )


class StudyPlanSubject(Base):
    __tablename__ = "study_plan_subjects"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "plan_id"],
            ["study_plans.user_id", "study_plans.id"],
            name="fk_study_plan_subjects_plan",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "subject_id"],
            ["subjects.user_id", "subjects.id"],
            name="fk_study_plan_subjects_owner_subject",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_study_plan_subjects_user_subject_plan",
            "user_id",
            "subject_id",
            "plan_id",
        ),
    )


class StudyPlanActivity(Base):
    __tablename__ = "study_plan_activities"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "plan_id", "subject_id"],
            [
                "study_plan_subjects.user_id",
                "study_plan_subjects.plan_id",
                "study_plan_subjects.subject_id",
            ],
            name="fk_study_plan_activities_plan_subject",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "subject_id", "activity_id"],
            ["activities.user_id", "activities.subject_id", "activities.id"],
            name="fk_study_plan_activities_owner_subject_activity",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        UniqueConstraint(
            "user_id",
            "plan_id",
            "subject_id",
            "activity_id",
            name="uq_study_plan_activities_owner_context",
        ),
        Index(
            "ix_study_plan_activities_user_subject_activity",
            "user_id",
            "subject_id",
            "activity_id",
        ),
    )


class StudyPlanSession(Base):
    __tablename__ = "study_plan_sessions"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    study_session_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "plan_id", "subject_id"],
            [
                "study_plan_subjects.user_id",
                "study_plan_subjects.plan_id",
                "study_plan_subjects.subject_id",
            ],
            name="fk_study_plan_sessions_plan_subject",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "subject_id", "study_session_id"],
            [
                "study_sessions.user_id",
                "study_sessions.subject_id",
                "study_sessions.id",
            ],
            name="fk_study_plan_sessions_owner_subject_session",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        UniqueConstraint(
            "user_id",
            "plan_id",
            "subject_id",
            "study_session_id",
            name="uq_study_plan_sessions_owner_context",
        ),
        Index(
            "ix_study_plan_sessions_user_subject_session",
            "user_id",
            "subject_id",
            "study_session_id",
        ),
    )


class StudyPlanDecision(Base):
    __tablename__ = "study_plan_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    field_path: Mapped[str | None] = mapped_column(Text)
    proposed_value: Mapped[Any | None] = mapped_column(JSONB)
    chosen_value: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "plan_id"],
            ["study_plans.user_id", "study_plans.id"],
            name="fk_study_plan_decisions_plan",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        CheckConstraint(
            "action IN ('accepted','edited','rejected','regenerated')",
            name="ck_study_plan_decisions_action",
        ),
        CheckConstraint(
            "field_path IS NULL OR (char_length(field_path) BETWEEN 1 AND 200 "
            "AND field_path = btrim(field_path) "
            "AND field_path !~ '^[[:space:]]*$')",
            name="ck_study_plan_decisions_field_path",
        ),
        CheckConstraint(
            "(proposed_value IS NULL OR "
            "octet_length(proposed_value::text) <= 65536) AND "
            "(chosen_value IS NULL OR octet_length(chosen_value::text) <= 65536)",
            name="ck_study_plan_decisions_value_size",
        ),
        CheckConstraint(
            "(action = 'accepted' AND proposed_value IS NOT NULL "
            "AND chosen_value IS NOT NULL) OR "
            "(action = 'edited' AND field_path IS NOT NULL "
            "AND proposed_value IS NOT NULL AND chosen_value IS NOT NULL "
            "AND proposed_value IS DISTINCT FROM chosen_value) OR "
            "(action IN ('rejected','regenerated') "
            "AND proposed_value IS NOT NULL AND chosen_value IS NULL)",
            name="ck_study_plan_decisions_values",
        ),
        CheckConstraint("isfinite(created_at)", name="ck_study_plan_decisions_time"),
        Index(
            "ix_study_plan_decisions_user_plan_created",
            "user_id",
            "plan_id",
            "created_at",
            "id",
        ),
    )


class StudyChallenge(Base):
    __tablename__ = "study_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[int | None] = mapped_column(Integer)
    activity_id: Mapped[int | None] = mapped_column(Integer)
    study_session_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    generation_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "plan_id"],
            ["study_plans.user_id", "study_plans.id"],
            name="fk_study_challenges_plan",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "plan_id", "subject_id"],
            [
                "study_plan_subjects.user_id",
                "study_plan_subjects.plan_id",
                "study_plan_subjects.subject_id",
            ],
            name="fk_study_challenges_plan_subject",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "plan_id", "subject_id", "activity_id"],
            [
                "study_plan_activities.user_id",
                "study_plan_activities.plan_id",
                "study_plan_activities.subject_id",
                "study_plan_activities.activity_id",
            ],
            name="fk_study_challenges_plan_activity",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "plan_id", "subject_id", "study_session_id"],
            [
                "study_plan_sessions.user_id",
                "study_plan_sessions.plan_id",
                "study_plan_sessions.subject_id",
                "study_plan_sessions.study_session_id",
            ],
            name="fk_study_challenges_plan_session",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "subject_id", "activity_id", "study_session_id"],
            [
                "study_sessions.user_id",
                "study_sessions.subject_id",
                "study_sessions.activity_id",
                "study_sessions.id",
            ],
            name="fk_study_challenges_session_activity_consistency",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 100 AND title = btrim(title) "
            "AND title !~ '^[[:space:]]*$'",
            name="ck_study_challenges_title",
        ),
        CheckConstraint(
            "char_length(description) BETWEEN 1 AND 2000 "
            "AND description = btrim(description) "
            "AND description !~ '^[[:space:]]*$'",
            name="ck_study_challenges_description",
        ),
        CheckConstraint(
            "target_type IN ('study_minutes','activity_completion',"
            "'session_completion','subject_mastery','custom')",
            name="ck_study_challenges_target_type",
        ),
        CheckConstraint(
            "CASE WHEN jsonb_typeof(target_value) <> 'object' "
            "OR octet_length(target_value::text) NOT BETWEEN 2 AND 4096 "
            "THEN false "
            "WHEN target_type = 'study_minutes' THEN "
            "(subject_id IS NOT NULL OR study_session_id IS NOT NULL) "
            "AND target_value ? 'minutes' "
            "AND target_value - 'minutes' = '{}'::jsonb "
            "AND jsonb_typeof(target_value->'minutes') = 'number' "
            "AND CASE WHEN target_value->>'minutes' ~ '^[1-9][0-9]{0,3}$' "
            "THEN (target_value->>'minutes')::integer BETWEEN 1 AND 1440 "
            "ELSE false END "
            "WHEN target_type = 'activity_completion' THEN "
            "activity_id IS NOT NULL "
            'AND target_value = \'{"status":"completed"}\'::jsonb '
            "WHEN target_type = 'session_completion' THEN "
            "study_session_id IS NOT NULL "
            'AND target_value = \'{"lifecycle":"finished"}\'::jsonb '
            "WHEN target_type = 'subject_mastery' THEN "
            "subject_id IS NOT NULL "
            "AND target_value ?& ARRAY['criterion','threshold'] "
            "AND target_value - 'criterion' - 'threshold' = '{}'::jsonb "
            "AND jsonb_typeof(target_value->'criterion') = 'string' "
            "AND char_length(btrim(target_value->>'criterion')) BETWEEN 1 AND 200 "
            "AND CASE WHEN jsonb_typeof(target_value->'threshold') = 'number' "
            "AND target_value->>'threshold' ~ '^(100|[1-9]?[0-9])$' "
            "THEN (target_value->>'threshold')::integer BETWEEN 1 AND 100 "
            "ELSE false END "
            "WHEN target_type = 'custom' THEN target_value <> '{}'::jsonb "
            "ELSE false END",
            name="ck_study_challenges_target_value",
        ),
        CheckConstraint(
            "(subject_id IS NOT NULL) OR "
            "(activity_id IS NULL AND study_session_id IS NULL)",
            name="ck_study_challenges_resource_subject",
        ),
        CheckConstraint(
            "(start_at IS NULL OR isfinite(start_at)) AND "
            "(deadline IS NULL OR isfinite(deadline)) AND "
            "(start_at IS NULL OR deadline IS NULL OR deadline >= start_at)",
            name="ck_study_challenges_dates",
        ),
        CheckConstraint(
            "status IN ('pending','in_progress','completed','failed','cancelled')",
            name="ck_study_challenges_status",
        ),
        CheckConstraint("source IN ('ai','manual')", name="ck_study_challenges_source"),
        CheckConstraint(
            "jsonb_typeof(generation_criteria) = 'object' "
            "AND generation_criteria <> '{}'::jsonb "
            "AND octet_length(generation_criteria::text) <= 16384",
            name="ck_study_challenges_generation_criteria",
        ),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND updated_at >= created_at",
            name="ck_study_challenges_timestamps",
        ),
        Index(
            "ix_study_challenges_user_status_deadline",
            "user_id",
            "status",
            "deadline",
            "id",
        ),
        Index(
            "ix_study_challenges_user_plan_status_deadline",
            "user_id",
            "plan_id",
            "status",
            "deadline",
            "id",
        ),
        Index(
            "ix_study_challenges_plan_subject_activity",
            "user_id",
            "plan_id",
            "subject_id",
            "activity_id",
        ),
        Index(
            "ix_study_challenges_plan_subject_session",
            "user_id",
            "plan_id",
            "subject_id",
            "study_session_id",
        ),
        Index(
            "ix_study_challenges_user_subject_activity_session",
            "user_id",
            "subject_id",
            "activity_id",
            "study_session_id",
        ),
    )


__all__ = [
    "StudyChallenge",
    "StudyPlan",
    "StudyPlanActivity",
    "StudyPlanDecision",
    "StudyPlanSession",
    "StudyPlanSubject",
]
