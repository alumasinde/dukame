"""Shared catalogue schema helpers for consistent create/update validation."""

from __future__ import annotations

from typing import Any

ALLOWED_CATALOGUE_STATUSES = frozenset({"active", "draft", "archived"})


def reject_null_fields(data: Any, fields: tuple[str, ...]) -> Any:
    """Reject explicit nulls for fields that must remain set when present in a partial update."""
    if isinstance(data, dict):
        for field in fields:
            if field in data and data[field] is None:
                raise ValueError(f"{field} cannot be null")
    return data


def normalize_optional_blank_str(value: str | None) -> str | None:
    """Treat blank optional strings as cleared (None) rather than empty unique keys."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def validate_catalogue_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in ALLOWED_CATALOGUE_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(ALLOWED_CATALOGUE_STATUSES))}")
    return normalized
