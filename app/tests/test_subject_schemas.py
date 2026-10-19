import pytest
from pydantic import ValidationError

from app.schemas.subject_create import SubjectCreate
from app.schemas.subject_write import SubjectWrite
from app.subjects.catalog import COLOR_BASES, COLOR_SHADES

PAYLOAD = dict(
    name="Matemáticas", difficulty="medium", color_base="blue", color_shade=300
)


def test_name_normalization_limits_and_defaults():
    value = SubjectCreate(**{**PAYLOAD, "name": "  Cafe\u0301  "})
    assert value.name == "Café" and value.status == "active"
    assert SubjectWrite(**{**PAYLOAD, "name": "🚀" * 20}).name == "🚀" * 20


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": " "},
        {"name": "a" * 21},
        {"name": "a\nb"},
        {"name": "a\u0000b"},
        {"name": None},
        {"difficulty": "Fácil"},
        {"status": "Activa"},
        {"color_base": "#fff"},
        {"color_base": "Blue"},
        {"color_shade": 50},
        {"color_shade": "300"},
        {"color_shade": 300.0},
        {"color_shade": True},
        {"user_id": 1},
        {"active_slot": 1},
    ],
)
def test_invalid_create(overrides):
    with pytest.raises(ValidationError):
        SubjectCreate(**{**PAYLOAD, **overrides})


def test_update_cannot_change_status_and_requires_all_fields():
    with pytest.raises(ValidationError):
        SubjectWrite(**{**PAYLOAD, "status": "archived"})
    with pytest.raises(ValidationError):
        SubjectWrite(name="Only name")


def test_all_catalog_pairs_are_valid():
    for base in COLOR_BASES:
        for shade in COLOR_SHADES:
            assert SubjectCreate(
                **{**PAYLOAD, "color_base": base, "color_shade": shade}
            )
