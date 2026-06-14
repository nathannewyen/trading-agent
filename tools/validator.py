"""Input validation helpers for ticker symbols and common agent parameters."""

import re

_TICKER_RE = re.compile(r"^[A-Z]{1,6}(\.[A-Z]{1,2})?$")
_VALID_PERIODS = frozenset({"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"})
_VALID_SECTORS = frozenset({"tech", "technology", "energy", "financials", "finance",
                             "healthcare", "health", "consumer"})


class ValidationError(ValueError):
    pass


def validate_ticker(ticker: str) -> str:
    """Normalise and validate a stock ticker symbol.

    Raises ValidationError if the ticker is invalid.
    Returns the uppercased, stripped ticker on success.
    """
    if not ticker:
        raise ValidationError("Ticker cannot be empty.")
    t = ticker.strip().upper()
    if t.isdigit():
        raise ValidationError(f"Invalid ticker {t!r}: must contain letters.")
    if not _TICKER_RE.match(t):
        raise ValidationError(
            f"Invalid ticker {t!r}: must be 1-6 uppercase letters, optionally followed by a dot and 1-2 letters."
        )
    return t


def validate_period(period: str) -> str:
    """Validate a yfinance period string.  Returns the period unchanged on success."""
    if period not in _VALID_PERIODS:
        raise ValidationError(
            f"Invalid period {period!r}. Must be one of: {sorted(_VALID_PERIODS)}"
        )
    return period


def validate_sector(sector: str) -> str:
    """Validate and normalise a sector name. Returns the lowercased sector on success."""
    s = sector.strip().lower()
    if s not in _VALID_SECTORS:
        raise ValidationError(
            f"Unknown sector {sector!r}. Must be one of: {sorted(_VALID_SECTORS)}"
        )
    return s


def validate_positive_float(value: float, name: str = "value") -> float:
    """Ensure *value* is a positive finite float."""
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
    if value <= 0:
        raise ValidationError(f"{name} must be positive, got {value}")
    import math
    if not math.isfinite(value):
        raise ValidationError(f"{name} must be finite, got {value}")
    return float(value)
