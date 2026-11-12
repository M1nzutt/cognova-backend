import pytest

from app.analytics.structures.analytics_resource import AnalyticsResource
from app.analytics.structures.resource_directory import ResourceDirectory


def test_resource_directory_resizes_updates_and_removes():
    directory = ResourceDirectory()
    resources = [
        AnalyticsResource("activity", index + 1, f"Actividad {index}")
        for index in range(100)
    ]
    for resource in resources:
        directory.put(resource)
    assert len(directory) == 100
    assert directory.get(("activity", 37)) == resources[36]
    revised = AnalyticsResource("activity", 37, "Trabajo revisado")
    directory.put(revised)
    assert len(directory) == 100
    assert directory.get(revised.key) == revised
    assert directory.remove(revised.key)
    assert directory.get(revised.key) is None
    assert not directory.remove(revised.key)
    assert len(directory) == 99


def test_resource_directory_rejects_invalid_resources():
    directory = ResourceDirectory()
    with pytest.raises(ValueError):
        directory.put(AnalyticsResource("", 1, "Nombre"))
    with pytest.raises(ValueError):
        directory.put(AnalyticsResource("subject", 0, "Materia"))
