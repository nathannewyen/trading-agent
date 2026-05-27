"""Unit tests for tools/technicals.py — RSI, Bollinger Bands, volume spike."""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.technicals import _compute_rsi, get_technicals


# --- _compute_rsi ---

def _make_close(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def test_rsi_overbought():
    # 15 days of consistent gains should push RSI near 100
    prices = [float(100 + i * 2) for i in range(20)]
    rsi = _compute_rsi(_make_close(prices))
    assert rsi > 70, f"Expected overbought RSI, got {rsi}"


def test_rsi_oversold():
    # 15 days of consistent losses should push RSI near 0
    prices = [float(200 - i * 2) for i in range(20)]
    rsi = _compute_rsi(_make_close(prices))
    assert rsi < 30, f"Expected oversold RSI, got {rsi}"


def test_rsi_clipped_to_100_on_zero_loss():
    # All gains — avg_loss == 0 — should return exactly 100.0
    prices = [float(100 + i) for i in range(20)]
    rsi = _compute_rsi(_make_close(prices))
    assert rsi == 100.0


def test_rsi_range():
    np.random.seed(42)
    prices = list(np.cumprod(1 + np.random.normal(0, 0.01, 50)) * 100)
    rsi = _compute_rsi(_make_close(prices))
    assert 0.0 <= rsi <= 100.0


# --- Bollinger Bands (via get_technicals stub) ---

def test_bollinger_fields_present(monkeypatch):
    """get_technicals should return bb_upper, bb_mid, bb_lower, bb_pct_b."""
    import yfinance as yf

    # Build a minimal fake history DataFrame with 60 rows
    np.random.seed(1)
    prices = list(np.cumprod(1 + np.random.normal(0, 0.01, 60)) * 150)
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    fake_hist = pd.DataFrame(
        {
            "Close": prices,
            "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices],
            "Volume": [1_000_000] * 60,
        },
        index=idx,
    )

    class FakeTicker:
        def history(self, period="1y"):
            return fake_hist

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_technicals("FAKE")
    assert "bb_upper" in result
    assert "bb_mid" in result
    assert "bb_lower" in result
    assert "bb_pct_b" in result
    assert result["bb_upper"] >= result["bb_mid"] >= result["bb_lower"]


# --- Volume spike ---

def test_volume_spike_detected(monkeypatch):
    """volume_spike should be True when today's volume is > 2x 30-day avg."""
    import yfinance as yf

    np.random.seed(2)
    prices = list(np.cumprod(1 + np.random.normal(0, 0.01, 60)) * 100)
    normal_vol = [500_000] * 59
    spike_vol = [500_000 * 5]  # 5x the average — well above 2x threshold
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    fake_hist = pd.DataFrame(
        {
            "Close": prices,
            "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices],
            "Volume": normal_vol + spike_vol,
        },
        index=idx,
    )

    class FakeTicker:
        def history(self, period="1y"):
            return fake_hist

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_technicals("FAKE")
    assert result["volume_spike"] is True


def test_volume_spike_false_on_normal_volume(monkeypatch):
    """volume_spike should be False when volume is within normal range."""
    import yfinance as yf

    np.random.seed(3)
    prices = list(np.cumprod(1 + np.random.normal(0, 0.01, 60)) * 100)
    vol = [500_000] * 60  # flat volume — no spike
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    fake_hist = pd.DataFrame(
        {
            "Close": prices,
            "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices],
            "Volume": vol,
        },
        index=idx,
    )

    class FakeTicker:
        def history(self, period="1y"):
            return fake_hist

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_technicals("FAKE")
    assert result["volume_spike"] is False


# --- Graceful fallback for short history ---

def test_short_history_sma50_is_none(monkeypatch):
    """With < 50 days of history, sma_50 should be None rather than NaN/crash."""
    import yfinance as yf

    prices = [float(100 + i) for i in range(30)]
    idx = pd.date_range("2024-01-01", periods=30, freq="B")
    fake_hist = pd.DataFrame(
        {
            "Close": prices,
            "High": [p * 1.01 for p in prices],
            "Low": [p * 0.99 for p in prices],
            "Volume": [200_000] * 30,
        },
        index=idx,
    )

    class FakeTicker:
        def history(self, period="1y"):
            return fake_hist

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_technicals("FAKE")
    assert result["sma_50"] is None
    assert result["sma_200"] is None
    assert result.get("above_50sma") is None
