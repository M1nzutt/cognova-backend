import json
import unicodedata
from typing import Any


def normalize_text(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value).strip()
    return value


def has_disallowed_controls(value: str) -> bool:
    return any(
        unicodedata.category(character) in {"Cc", "Cs"} and character not in "\n\r\t"
        for character in value
    )


def json_size(value: Any) -> int:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("Value must contain only JSON-compatible data") from None
    return len(encoded)


__all__ = ["has_disallowed_controls", "json_size", "normalize_text"]
