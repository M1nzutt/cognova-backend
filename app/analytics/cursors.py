"""Opaque, filter-bound pagination cursors for read-only Analytics routes."""

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.analytics.structures.entries import TimelineEvent
from app.core.domain_error import DomainError


def _fingerprint(filters: dict[str, Any]) -> str:
    encoded = json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]


def _encode(payload: list[Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str) -> list[Any]:
    try:
        if not cursor or any(
            character
            not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
            for character in cursor
        ):
            raise ValueError
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise DomainError("ANALYTICS_CURSOR_INVALID") from exc


def encode_timeline_cursor(
    event: TimelineEvent,
    start: datetime,
    end: datetime,
    category: str | None,
) -> str:
    filters = {
        "from": start.astimezone(timezone.utc).isoformat(),
        "to": end.astimezone(timezone.utc).isoformat(),
        "category": category,
    }
    return _encode(
        [
            1,
            _fingerprint(filters),
            event.occurred_at.astimezone(timezone.utc).isoformat(),
            event.key[1],
            event.resource_id,
            event.occurrence_id,
            event.event_type,
        ]
    )


def decode_timeline_cursor(
    cursor: str,
    start: datetime,
    end: datetime,
    category: str | None,
) -> tuple[datetime, int, int, int, str]:
    payload = _decode(cursor)
    expected = _fingerprint(
        {
            "from": start.astimezone(timezone.utc).isoformat(),
            "to": end.astimezone(timezone.utc).isoformat(),
            "category": category,
        }
    )
    try:
        version, fingerprint, at_value, rank, resource_id, occurrence_id, event_type = (
            payload
        )
        at = datetime.fromisoformat(at_value)
        if (
            version != 1
            or fingerprint != expected
            or at.tzinfo is None
            or isinstance(rank, bool)
            or rank not in range(5)
            or isinstance(resource_id, bool)
            or not isinstance(resource_id, int)
            or resource_id <= 0
            or isinstance(occurrence_id, bool)
            or not isinstance(occurrence_id, int)
            or occurrence_id < 0
            or not isinstance(event_type, str)
            or not event_type
            or len(event_type) > 80
        ):
            raise ValueError
        return at.astimezone(timezone.utc), rank, resource_id, occurrence_id, event_type
    except (TypeError, ValueError, OverflowError) as exc:
        raise DomainError("ANALYTICS_CURSOR_INVALID") from exc


__all__ = [
    "decode_timeline_cursor",
    "encode_timeline_cursor",
]
