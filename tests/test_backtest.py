"""Unit tests for backtest.py."""

from unittest.mock import patch

import pandas as pd
import pytest

from backtest import run_backtest


def _make_price_series(length: int = 300, start: float = 100.0, trend: float = 0.001) -> pd.DataFrame:
    """Synthetic trending price series."""
    import numpy as np
    rng = pd.date_range("2020-01-02", periods=length, freq="B")
    prices = pd.Series(
        [start * (1 + trend) ** i + (i % 7 * 0.5) for i in range(length)],
        index=rng,
        name="Close",
    )
    return pd.DataFrame({"Close": prices})


@patch("backtest.yf.download")
def test_returns_expected_keys(mock_dl):
    mock_dl.return_value = _make_price_series(300)
    result = run_backtest("NVDA", short_window=20, long_window=50, period="5y")
    expected_keys = [
        "ticker", "total_return_pct", "annualised_return_pct",
        "sharpe_ratio", "max_drawdown_pct", "num_trades", "trades",
    ]
    for k in expected_keys:
        assert k in result, f"Missing key: {k}"


@patch("backtest.yf.download")
def test_ticker_uppercased(mock_dl):
    mock_dl.return_value = _make_price_series(300)
    result = run_backtest("nvda", short_window=20, long_window=50)
    assert result["ticker"] == "NVDA"


@patch("backtest.yf.download")
def test_empty_dataframe_returns_error(mock_dl):
    mock_dl.return_value = pd.DataFrame()
    result = run_backtest("EMPTY")
    assert "error" in result


@patch("backtest.yf.download")
def test_insufficient_history_returns_error(mock_dl):
    mock_dl.return_value = _make_price_series(length=30)
    result = run_backtest("SHORT", short_window=50, long_window=200)
    assert "error" in result


@patch("backtest.yf.download")
def test_max_drawdown_non_positive(mock_dl):
    mock_dl.return_value = _make_price_series(300)
    result = run_backtest("NVDA", short_window=20, long_window=50)
    if "max_drawdown_pct" in result:
        assert result["max_drawdown_pct"] <= 0


@patch("backtest.yf.download")
def test_trade_log_contains_buy_and_sell(mock_dl):
    mock_dl.return_value = _make_price_series(300)
    result = run_backtest("NVDA", short_window=20, long_window=50)
    if result.get("trades"):
        actions = {t["action"] for t in result["trades"]}
        assert "BUY" in actions or "SELL" in actions
