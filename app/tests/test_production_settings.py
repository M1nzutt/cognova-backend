import pytest
from pydantic import ValidationError

from app.core.settings import Settings


@pytest.mark.parametrize(
    "overrides",
    [
        {"cors_allowed_origins": ["*"]},
        {"cors_allowed_origins": ["https://*.example.com"]},
        {"cors_allowed_origins": ["https://example.com/path"]},
        {"environment": "production", "cookie_secure": False},
        {"environment": "production", "cors_allowed_origins": []},
        {"environment": "production", "cors_allowed_origins": ["http://example.com"]},
        {"access_token_expire_minutes": 60},
    ],
)
def test_rejects_unsafe_production_configuration(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_production_accepts_https_allowlist():
    settings = Settings(
        _env_file=None,
        environment="production",
        cors_allowed_origins=["https://cognova.example"],
    )
    assert settings.cookie_secure
    assert "sslmode=require" in settings.database_url.get_secret_value()


@pytest.mark.parametrize("mode", ["disable", "allow", "prefer"])
def test_production_rejects_optional_database_tls(mode):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            cors_allowed_origins=["https://cognova.example"],
            database_url=f"postgresql://user:password@db:5432/cognova?sslmode={mode}",
        )


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_render_connection_url_is_normalized_without_losing_password(scheme):
    settings = Settings(
        _env_file=None,
        database_url=f"{scheme}://user:pass%40word@db.internal:5432/cognova?sslmode=require",
    )
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url.get_secret_value())
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "pass@word"
    assert url.query["sslmode"] == "require"
