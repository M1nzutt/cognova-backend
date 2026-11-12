"""Prefix search over owned academic resources using a manual character trie."""

import unicodedata
from collections.abc import Iterator

from app.analytics.structures.analytics_resource import AnalyticsResource


def normalize_search_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )


class SearchBranch:
    __slots__ = ("children", "resources")

    def __init__(self) -> None:
        self.children: dict[str, SearchBranch] = {}
        self.resources: dict[tuple[str, int], AnalyticsResource] = {}


class AcademicFinder:
    """Finds deduplicated resources by normalized title prefix."""

    def __init__(self) -> None:
        self._root = SearchBranch()
        self._size = 0
        self._registered: dict[tuple[str, int], str] = {}

    def __len__(self) -> int:
        return self._size

    def add(self, resource: AnalyticsResource) -> None:
        normalized = normalize_search_text(resource.title.strip())
        if not normalized or not resource.resource_type:
            raise ValueError("Search resource requires a type and title")
        if resource.resource_id <= 0:
            raise ValueError("Search resource ID must be positive")
        previous = self._registered.get(resource.key)
        if previous is not None and previous != normalized:
            old_branch = self._branch(previous)
            assert old_branch is not None
            old_branch.resources.pop(resource.key, None)
        elif previous == normalized:
            branch = self._branch(normalized)
            assert branch is not None
            branch.resources[resource.key] = resource
            return
        branch = self._root
        for character in normalized:
            branch = branch.children.setdefault(character, SearchBranch())
        if previous is None:
            self._size += 1
        self._registered[resource.key] = normalized
        branch.resources[resource.key] = resource

    def search(
        self,
        prefix: str,
        after_key: tuple[str, str, int] | None = None,
        limit: int | None = None,
    ) -> list[AnalyticsResource]:
        normalized = normalize_search_text(prefix.strip())
        if not normalized:
            raise ValueError("Search prefix cannot be empty")
        branch = self._branch(normalized)
        if branch is None:
            return []
        matching = list(self._resources(branch))
        matching.sort(key=self.sort_key)
        if after_key is not None:
            matching = [item for item in matching if self.sort_key(item) > after_key]
        return matching if limit is None else matching[:limit]

    @staticmethod
    def sort_key(resource: AnalyticsResource) -> tuple[str, str, int]:
        return (
            normalize_search_text(resource.title.strip()),
            resource.resource_type,
            resource.resource_id,
        )

    def _branch(self, normalized: str) -> SearchBranch | None:
        branch: SearchBranch | None = self._root
        for character in normalized:
            if branch is None:
                return None
            branch = branch.children.get(character)
            if branch is None:
                return None
        return branch

    @classmethod
    def _resources(cls, branch: SearchBranch) -> Iterator[AnalyticsResource]:
        yield from branch.resources.values()
        for character in sorted(branch.children):
            yield from cls._resources(branch.children[character])


__all__ = ["AcademicFinder", "normalize_search_text"]
