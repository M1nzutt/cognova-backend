"""Filter-bound cursors for academic prefix search."""

from typing import Any

from app.analytics.cursors import _decode, _encode, _fingerprint
from app.analytics.structures.academic_finder import normalize_search_text
from app.core.domain_error import DomainError


def encode_search_cursor(
    resource: tuple[str, str, int], prefix: str, resource_type: str | None
) -> str:
    filters = {
        "prefix": normalize_search_text(prefix.strip()),
        "type": resource_type,
    }
    return _encode([1, _fingerprint(filters), *resource])


def decode_search_cursor(
    cursor: str, prefix: str, resource_type: str | None
) -> tuple[str, str, int]:
    payload: list[Any] = _decode(cursor)
    expected = _fingerprint(
        {"prefix": normalize_search_text(prefix.strip()), "type": resource_type}
    )
    try:
        version, fingerprint, normalized_title, found_type, resource_id = payload
        if (
            version != 1
            or fingerprint != expected
            or not isinstance(normalized_title, str)
            or not normalized_title
            or not isinstance(found_type, str)
            or not found_type
            or isinstance(resource_id, bool)
            or not isinstance(resource_id, int)
            or resource_id <= 0
        ):
            raise ValueError
        return normalized_title, found_type, resource_id
    except (TypeError, ValueError) as exc:
        raise DomainError("ANALYTICS_CURSOR_INVALID") from exc


__all__ = ["decode_search_cursor", "encode_search_cursor"]
