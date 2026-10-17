from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.main import create_app


def test_openapi_matches_minimal_registration_and_onboarding_dtos():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        schema = client.get("/openapi.json").json()
    models = schema["components"]["schemas"]
    register = models["RegisterRequest"]
    assert set(register["required"]) == {"name", "email", "password"}
    assert set(register["properties"]) == set(register["required"])
    assert register["additionalProperties"] is False
    assert register["properties"]["name"]["maxLength"] == 30
    assert register["properties"]["email"]["maxLength"] == 50
    assert register["properties"]["password"]["minLength"] == 8
    assert register["properties"]["password"]["maxLength"] == 12
    assert "academic_goal" not in models["UserResponse"]["properties"]
    assert "onboarding" in models["UserResponse"]["required"]
    assert len(models["QuestionnaireAnswers"]["required"]) == 10
    assert "expected_revision" in models["QuestionnaireUpdateRequest"]["required"]
    assert "409" in schema["paths"]["/api/v1/questionnaire"]["put"]["responses"]
    assert "201" in schema["paths"]["/api/v1/questionnaire"]["post"]["responses"]
    for path in ("/api/v1/questionnaire/catalog", "/api/v1/questionnaire/history"):
        assert schema["paths"][path]["get"]["security"] == [{"HTTPBearer": []}]
