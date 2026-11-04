import pytest

from app.study_plans.learning_plan_map import LearningPlanMap


def test_learning_plan_map_builds_and_walks_resource_hierarchy():
    hierarchy = LearningPlanMap(8, "Examen de cálculo")
    hierarchy.add(
        key="subject:3",
        kind="subject",
        label="Cálculo",
        parent_key="plan:8",
    )
    hierarchy.add(
        key="activity:12",
        kind="activity",
        label="Guía 2",
        parent_key="subject:3",
    )
    hierarchy.add(
        key="session:16",
        kind="study_session",
        label="Repaso",
        parent_key="subject:3",
    )
    hierarchy.add(
        key="challenge:21",
        kind="challenge",
        label="Resolver cinco ejercicios",
        parent_key="activity:12",
    )

    assert [branch.key for branch in hierarchy.walk()] == [
        "plan:8",
        "subject:3",
        "activity:12",
        "challenge:21",
        "session:16",
    ]
    assert hierarchy.find("challenge:21") is not None
    assert hierarchy.as_dict()["children"][0]["children"][0]["children"][0][
        "kind"
    ] == "challenge"


def test_learning_plan_map_rejects_duplicate_or_missing_parent():
    hierarchy = LearningPlanMap(8, "Examen de cálculo")
    with pytest.raises(KeyError):
        hierarchy.add(
            key="activity:12",
            kind="activity",
            label="Guía 2",
            parent_key="subject:3",
        )
    hierarchy.add(
        key="subject:3",
        kind="subject",
        label="Cálculo",
        parent_key="plan:8",
    )
    with pytest.raises(ValueError):
        hierarchy.add(
            key="subject:3",
            kind="subject",
            label="Cálculo duplicado",
            parent_key="plan:8",
        )
