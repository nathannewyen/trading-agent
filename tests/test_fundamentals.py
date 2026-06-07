"""Unit tests for tools/fundamentals.py."""

from unittest.mock import MagicMock, patch

import pytest

from tools.fundamentals import get_fundamentals


MOCK_INFO = {
    "marketCap": 3_000_000_000_000,
    "enterpriseValue": 2_900_000_000_000,
    "priceToBook": 45.2,
    "priceToSalesTrailing12Months": 28.5,
    "debtToEquity": 15.3,
    "currentRatio": 1.05,
    "returnOnEquity": 1.47,
    "returnOnAssets": 0.22,
    "freeCashflow": 90_000_000_000,
    "operatingMargins": 0.31,
    "grossMargins": 0.46,
    "revenueGrowth": 0.09,
    "earningsGrowth": 0.11,
}


@patch("tools.fundamentals.cache.get", return_value=None)
@patch("tools.fundamentals.cache.set")
@patch("tools.fundamentals.yf.Ticker")
def test_returns_expected_keys(mock_ticker, mock_set, mock_get):
    mock_ticker.return_value.info = MOCK_INFO
    result = get_fundamentals("AAPL")
    assert result["ticker"] == "AAPL"
    assert "debt_to_equity" in result
    assert "fcf_yield_pct" in result
    assert "return_on_equity" in result


@patch("tools.fundamentals.cache.get", return_value=None)
@patch("tools.fundamentals.cache.set")
@patch("tools.fundamentals.yf.Ticker")
def test_fcf_yield_computed_correctly(mock_ticker, mock_set, mock_get):
    mock_ticker.return_value.info = MOCK_INFO
    result = get_fundamentals("AAPL")
    expected = round(90e9 / 3e12 * 100, 2)
    assert result["fcf_yield_pct"] == pytest.approx(expected)


@patch("tools.fundamentals.cache.get", return_value=None)
@patch("tools.fundamentals.cache.set")
@patch("tools.fundamentals.yf.Ticker")
def test_missing_fields_return_none(mock_ticker, mock_set, mock_get):
    mock_ticker.return_value.info = {"marketCap": 1e9}
    result = get_fundamentals("XYZ")
    assert result["price_to_book"] is None
    assert result["fcf_yield_pct"] is None


@patch("tools.fundamentals.cache.get", return_value=None)
@patch("tools.fundamentals.cache.set")
@patch("tools.fundamentals.yf.Ticker")
def test_yfinance_error_returns_error_dict(mock_ticker, mock_set, mock_get):
    mock_ticker.side_effect = Exception("connection timeout")
    result = get_fundamentals("BAD")
    assert "error" in result


@patch("tools.fundamentals.cache.get")
def test_returns_cached_result(mock_get):
    cached = {"ticker": "NVDA", "debt_to_equity": 5.0}
    mock_get.return_value = cached
    result = get_fundamentals("NVDA")
    assert result == cached


@patch("tools.fundamentals.cache.get", return_value=None)
@patch("tools.fundamentals.cache.set")
@patch("tools.fundamentals.yf.Ticker")
def test_ticker_uppercased_in_result(mock_ticker, mock_set, mock_get):
    mock_ticker.return_value.info = MOCK_INFO
    result = get_fundamentals("msft")
    assert result["ticker"] == "MSFT"
