from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_study_plan_openapi_matches_nested_plan_and_challenge_contract():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        spec = client.get("/openapi.json").json()

    paths = spec["paths"]
    assert set(paths["/api/v1/study-plans/generate"]) == {"post"}
    assert set(paths["/api/v1/analysis/behavior"]) == {"post"}
    assert set(paths["/api/v1/study-plans"]) == {"get", "post"}
    assert set(paths["/api/v1/study-plans/{plan_id}"]) == {
        "get",
        "put",
        "delete",
    }
    for action in (
        "accept",
        "reject",
        "regenerate",
        "activate",
        "complete",
        "abandon",
        "undo",
    ):
        assert set(paths[f"/api/v1/study-plans/{{plan_id}}/{action}"]) == {"post"}
    assert set(paths["/api/v1/study-plans/{plan_id}/challenges"]) == {"get", "post"}
    assert set(paths["/api/v1/study-plans/{plan_id}/challenges/{challenge_id}"]) == {
        "get",
        "put",
    }
    for action in ("start", "complete", "fail", "cancel"):
        assert set(
            paths[
                f"/api/v1/study-plans/{{plan_id}}/challenges/{{challenge_id}}/{action}"
            ]
        ) == {"post"}

    delete = paths["/api/v1/study-plans/{plan_id}"]["delete"]
    confirm = next(item for item in delete["parameters"] if item["name"] == "confirm")
    assert confirm["required"] is True
    schemas = spec["components"]["schemas"]
    assert "StudyPlanDetail" in schemas
    detail = schemas["StudyPlanDetail"]["properties"]
    assert {"ai_proposal_snapshot", "explanation", "reasoning_summary"} <= set(detail)
    assert "AiPlanProposalSnapshot" in schemas
    assert {"schema_version", "plan", "proposed_challenges"} <= set(
        schemas["AiPlanProposalSnapshot"]["properties"]
    )
    assert "StudyChallengeResponse" in schemas
    assert "user_id" not in str(schemas)
    assert "/api/v1/challenges" not in paths
    assert "/api/v1/dependencies" not in paths
