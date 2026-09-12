from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.time import utc_now

# Statuses that still grant plan entitlements (mirrored from subscription service).
_ENTITLED_STATUSES = {"trial", "active", "past_due"}


def _feature_map(subscription: Any) -> dict[str, Any]:
    """Return the plan's configured feature values without assuming a schema."""
    plan = getattr(subscription, "plan", None)
    features = getattr(plan, "features", None) or []
    result: dict[str, Any] = {}
    for feature in features:
        key = getattr(feature, "feature_key", None)
        if key:
            result[str(key)] = getattr(feature, "value", None)
    return result


def is_subscription_entitled(subscription: Any) -> bool:
    """Whether the subscription currently grants plan features.

    Checks status and period end. Safe to call with None (returns False).
    """
    if subscription is None:
        return False
    status = getattr(subscription, "status", None)
    if status not in _ENTITLED_STATUSES:
        return False
    period_end = getattr(subscription, "current_period_end", None)
    if period_end is None:
        return True
    return period_end >= utc_now()


def feature_value(subscription: Any, feature_key: str, default: Any = None) -> Any:
    """Read a configured feature value from the subscribed plan."""
    if not feature_key:
        raise ValueError("feature_key must not be empty")
    if not is_subscription_entitled(subscription):
        return default
    return _feature_map(subscription).get(feature_key, default)


def has_feature(subscription: Any, feature_key: str) -> bool:
    """Whether a feature is explicitly enabled on the current plan."""
    value = feature_value(subscription, feature_key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "enabled", "on"}
    return False


def feature_limit(subscription: Any, feature_key: str) -> int | None:
    """Return a numeric feature limit; None means unlimited or not configured."""
    value = feature_value(subscription, feature_key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"unlimited", "infinite", "none"}:
            return None
        try:
            parsed = int(normalized)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def require_feature(subscription: Any, feature_key: str) -> None:
    """Raise 403 when the plan does not enable a requested feature."""
    if not is_subscription_entitled(subscription):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_inactive",
                "status": getattr(subscription, "status", None),
            },
        )
    if not has_feature(subscription, feature_key):
        raise HTTPException(
            status_code=403,
            detail={"code": "subscription_feature_required", "feature": feature_key},
        )


def require_within_limit(subscription: Any, feature_key: str, current_count: int) -> None:
    """Raise 403 when adding one more item would exceed a configured plan limit."""
    if current_count < 0:
        raise ValueError("current_count must not be negative")
    if not is_subscription_entitled(subscription):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_inactive",
                "status": getattr(subscription, "status", None),
            },
        )
    limit = feature_limit(subscription, feature_key)
    if limit is not None and current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "subscription_limit_reached",
                "feature": feature_key,
                "limit": limit,
                "current": current_count,
            },
        )
