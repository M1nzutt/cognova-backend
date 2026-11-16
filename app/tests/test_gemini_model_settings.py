import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.academic_intelligence.gemini_provider import MODEL, GeminiProvider
from app.core.settings import Settings
from app.tests.test_gemini_plan_codec import payload as payload


def test_missing_model_preserves_default():
    assert Settings(_env_file=None).gemini_model == MODEL


def test_model_is_loaded_from_backend_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    assert Settings(_env_file=None).gemini_model == "gemini-3.5-flash-lite"


@pytest.mark.parametrize("value", ["", "gpt-5", "gemini-x\nsecret", "../gemini-x"])
def test_invalid_model_is_rejected(monkeypatch, value):
    monkeypatch.setenv("GEMINI_MODEL", value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_configured_model_used_for_generation_and_safe_metadata(payload, caplog):
    create = Mock(return_value=SimpleNamespace(
        output_text=json.dumps(payload), status="completed"
    ))
    provider = GeminiProvider(
        None,
        model="gemini-3.5-flash-lite",
        client=SimpleNamespace(interactions=SimpleNamespace(create=create)),
    )
    with caplog.at_level("INFO"):
        provider.plan("{}")
    assert provider.model == "gemini-3.5-flash-lite"
    assert create.call_args.kwargs["model"] == provider.model
    assert create.call_count == 1
    assert "model=gemini-3.5-flash-lite" in caplog.text
    assert payload["objective"] not in caplog.text
