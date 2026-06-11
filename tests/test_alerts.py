"""Unit tests for tools/alerts.py."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.alerts import check_price_alert, list_alert_history


class FakeFastInfo:
    last_price = 500.0


@patch("tools.alerts.yf.Ticker")
@patch("tools.alerts._save_history")
@patch("tools.alerts._load_history", return_value={})
def test_triggered_above(mock_load, mock_save, mock_ticker):
    mock_ticker.return_value.fast_info = FakeFastInfo()
    result = check_price_alert("NVDA", threshold=450.0, direction="above")
    assert result["triggered"] is True
    assert result["current_price"] == 500.0


@patch("tools.alerts.yf.Ticker")
@patch("tools.alerts._save_history")
@patch("tools.alerts._load_history", return_value={})
def test_not_triggered_above(mock_load, mock_save, mock_ticker):
    mock_ticker.return_value.fast_info = FakeFastInfo()
    result = check_price_alert("NVDA", threshold=600.0, direction="above")
    assert result["triggered"] is False


@patch("tools.alerts.yf.Ticker")
@patch("tools.alerts._save_history")
@patch("tools.alerts._load_history", return_value={})
def test_triggered_below(mock_load, mock_save, mock_ticker):
    mock_ticker.return_value.fast_info = FakeFastInfo()
    result = check_price_alert("NVDA", threshold=600.0, direction="below")
    assert result["triggered"] is True


@patch("tools.alerts.yf.Ticker")
def test_invalid_direction_returns_error(mock_ticker):
    result = check_price_alert("NVDA", threshold=500.0, direction="sideways")
    assert "error" in result


@patch("tools.alerts.yf.Ticker")
def test_fetch_error_returns_error(mock_ticker):
    mock_ticker.side_effect = Exception("network failure")
    result = check_price_alert("BAD", threshold=100.0)
    assert "error" in result


@patch("tools.alerts.yf.Ticker")
@patch("tools.alerts._save_history")
@patch("tools.alerts._load_history", return_value={"last_fired": time.time()})
def test_cooldown_suppresses_repeated_alert(mock_load, mock_save, mock_ticker):
    mock_ticker.return_value.fast_info = FakeFastInfo()
    check_price_alert("NVDA", threshold=450.0, direction="above", cooldown_seconds=3600)
    mock_save.assert_not_called()


def test_list_history_empty_dir(tmp_path):
    with patch("tools.alerts.ALERTS_DIR", tmp_path / "nonexistent"):
        result = list_alert_history()
    assert result == []
