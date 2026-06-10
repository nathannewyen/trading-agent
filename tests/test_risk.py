"""Unit tests for tools/risk.py."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tools.risk import get_risk_metrics


def _make_returns(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2025-01-02", periods=len(values), freq="B"))


STOCK_RETS = _make_returns([0.01, -0.02, 0.015, 0.005, -0.01] * 60)
SPY_RETS = _make_returns([0.008, -0.015, 0.012, 0.003, -0.008] * 60)

_FAKE_CLOSE = pd.DataFrame({"Close": (1 + STOCK_RETS).cumprod()})
_FAKE_SPY_CLOSE = pd.DataFrame({"Close": (1 + SPY_RETS).cumprod()})


@patch("tools.risk.cache.get", return_value=None)
@patch("tools.risk.cache.set")
@patch("tools.risk.yf.download")
def test_returns_expected_keys(mock_dl, mock_set, mock_get):
    mock_dl.side_effect = [_FAKE_CLOSE, _FAKE_SPY_CLOSE]
    result = get_risk_metrics("NVDA")
    for key in ["beta", "annualised_volatility_pct", "sharpe_ratio", "max_drawdown_pct", "spy_correlation"]:
        assert key in result, f"Missing key: {key}"


@patch("tools.risk.cache.get", return_value=None)
@patch("tools.risk.cache.set")
@patch("tools.risk.yf.download")
def test_max_drawdown_is_negative(mock_dl, mock_set, mock_get):
    mock_dl.side_effect = [_FAKE_CLOSE, _FAKE_SPY_CLOSE]
    result = get_risk_metrics("NVDA")
    assert result["max_drawdown_pct"] <= 0


@patch("tools.risk.cache.get", return_value=None)
@patch("tools.risk.cache.set")
@patch("tools.risk.yf.download")
def test_empty_dataframe_returns_error(mock_dl, mock_set, mock_get):
    mock_dl.return_value = pd.DataFrame()
    result = get_risk_metrics("EMPTY")
    assert "error" in result


@patch("tools.risk.cache.get")
def test_returns_cached_result(mock_get):
    mock_get.return_value = {"ticker": "AAPL", "beta": 1.2}
    result = get_risk_metrics("AAPL")
    assert result["beta"] == 1.2


@patch("tools.risk.cache.get", return_value=None)
@patch("tools.risk.cache.set")
@patch("tools.risk.yf.download")
def test_download_exception_returns_error(mock_dl, mock_set, mock_get):
    mock_dl.side_effect = Exception("network error")
    result = get_risk_metrics("FAIL")
    assert "error" in result
