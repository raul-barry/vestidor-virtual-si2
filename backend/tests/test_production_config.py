import pytest
from pydantic import ValidationError
from app.core.config import Settings


def production(**overrides):
    return Settings(_env_file=None, environment="production", database_url="sqlite://",
                    secret_key=overrides.pop("secret_key", "a" * 48),
                    expose_reset_token=overrides.pop("expose_reset_token", False),
                    cors_origins=overrides.pop("cors_origins", "https://vestidor.example.com"), **overrides)


@pytest.mark.parametrize("overrides", [
    {"secret_key": "change-me-before-production"},
    {"secret_key": "REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS"},
    {"expose_reset_token": True},
    {"cors_origins": "*"},
])
def test_rejects_unsafe_production_settings(overrides):
    with pytest.raises(ValidationError):
        production(**overrides)


def test_accepts_explicit_production_settings():
    assert production().environment == "production"
