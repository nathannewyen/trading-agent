"""Unit tests for tools/validator.py."""

import pytest
from tools.validator import (
    ValidationError,
    validate_period,
    validate_positive_float,
    validate_sector,
    validate_ticker,
)


# --- validate_ticker ---

def test_valid_ticker():
    assert validate_ticker("NVDA") == "NVDA"


def test_valid_ticker_lowercase():
    assert validate_ticker("aapl") == "AAPL"


def test_valid_ticker_with_dot():
    assert validate_ticker("BRK.B") == "BRK.B"


def test_empty_ticker_raises():
    with pytest.raises(ValidationError, match="empty"):
        validate_ticker("")


def test_digit_only_ticker_raises():
    with pytest.raises(ValidationError, match="letters"):
        validate_ticker("12345")


def test_too_long_ticker_raises():
    with pytest.raises(ValidationError):
        validate_ticker("TOOLONGX")


# --- validate_period ---

def test_valid_period():
    assert validate_period("1y") == "1y"


def test_invalid_period_raises():
    with pytest.raises(ValidationError, match="period"):
        validate_period("3weeks")


# --- validate_sector ---

def test_valid_sector():
    assert validate_sector("tech") == "tech"


def test_sector_case_insensitive():
    assert validate_sector("ENERGY") == "energy"


def test_invalid_sector_raises():
    with pytest.raises(ValidationError, match="sector"):
        validate_sector("mining")


# --- validate_positive_float ---

def test_positive_float_ok():
    assert validate_positive_float(3.14) == pytest.approx(3.14)


def test_zero_raises():
    with pytest.raises(ValidationError, match="positive"):
        validate_positive_float(0.0)


def test_negative_raises():
    with pytest.raises(ValidationError, match="positive"):
        validate_positive_float(-5.0)


def test_non_number_raises():
    with pytest.raises(ValidationError, match="number"):
        validate_positive_float("abc")  # type: ignore
