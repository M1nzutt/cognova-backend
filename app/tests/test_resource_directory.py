import pytest

from app.analytics.structures.analytics_resource import AnalyticsResource
from app.analytics.structures.resource_directory import ResourceDirectory


def test_resource_directory_resizes_updates_and_removes():
    directory = ResourceDirectory()
    assert len(directory) == 0 and directory.values() == []
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


def test_resource_directory_resolves_linear_probe_collisions_after_removal():
    directory = ResourceDirectory()
    keys = []
    for identifier in range(1, 500):
        key = ("activity", identifier)
        if ResourceDirectory._hash(key) % directory._INITIAL_CAPACITY == 3:
            keys.append(identifier)
        if len(keys) == 3:
            break
    resources = [
        AnalyticsResource("activity", identifier, f"Tarea {identifier}")
        for identifier in keys
    ]
    for resource in resources:
        directory.put(resource)
    assert directory.remove(resources[0].key)
    assert directory.get(resources[1].key) == resources[1]
    assert directory.get(resources[2].key) == resources[2]
