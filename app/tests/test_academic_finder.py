import pytest

from app.analytics.structures.academic_finder import (
    AcademicFinder,
    normalize_search_text,
)
from app.analytics.structures.analytics_resource import AnalyticsResource


def test_academic_finder_normalizes_case_and_accents_and_deduplicates():
    finder = AcademicFinder()
    first = AnalyticsResource("subject", 1, "Física avanzada")
    finder.add(first)
    finder.add(first)
    finder.add(AnalyticsResource("activity", 2, "Fisica: laboratorio"))
    finder.add(AnalyticsResource("study_plan", 3, "Física de campos"))

    matches = finder.search("FISICA")

    assert [item.key for item in matches] == [
        ("subject", 1),
        ("study_plan", 3),
        ("activity", 2),
    ]
    assert len(finder) == 3
    assert normalize_search_text("Mecánica cuántica") == "mecanica cuantica"
    assert finder.search("quim") == []


def test_academic_finder_prefix_pagination_and_invalid_query():
    finder = AcademicFinder()
    for index, title in enumerate(("Análisis I", "Análisis II", "Anatomía"), start=1):
        finder.add(AnalyticsResource("subject", index, title))
    all_matches = finder.search("ana")
    assert len(finder.search("ana", limit=2)) == 2
    assert (
        finder.search("ana", after_key=finder.sort_key(all_matches[0]), limit=2)
        == all_matches[1:]
    )
    with pytest.raises(ValueError):
        finder.search("   ")
