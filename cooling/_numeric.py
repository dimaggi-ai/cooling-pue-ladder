"""Validation shared by the cooling admission boundary; no numeric coercion."""

import math


def finite_number(value, field, *, minimum=None, maximum=None,
                  positive=False, integral=False):
    """Require a finite Python int/float, excluding bool, within its domain."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number, excluding bool")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{field} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{field} must be > 0")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} must be <= {maximum}")
    if integral and value != int(value):
        raise ValueError(f"{field} must be integral-valued")
    return value


def identifier(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
