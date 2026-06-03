"""Unit tests for tools/macro.py — verify get_macro returns expected keys."""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.macro import get_macro

EXPECTED_KEYS = {
    "vix",
    "vix_signal",
    "ten_year_yield_pct",
    "yield_signal",
    "spy_price",
    "spy_trend",
    "regime",
}


def _make_history(n: int, base: float = 100.0, seed: int = 0) -> pd.DataFrame:
    np.random.seed(seed)
    prices = list(np.cumprod(1 + np.random.normal(0, 0.005, n)) * base)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "Close": prices,
            "High": [p * 1.005 for p in prices],
            "Low": [p * 0.995 for p in prices],
            "Volume": [1_000_000] * n,
        },
        index=idx,
    )


def test_get_macro_returns_expected_keys(monkeypatch):
    """get_macro must return all expected top-level keys."""
    import yfinance as yf

    histories = {
        "^VIX": _make_history(5, base=18.0, seed=1),
        "^TNX": _make_history(5, base=43.0, seed=2),   # 4.3% yield
        "SPY": _make_history(250, base=500.0, seed=3),
    }

    class FakeTicker:
        def __init__(self, t):
            self._t = t

        def history(self, period="1y"):
            return histories.get(self._t, pd.DataFrame())

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    result = get_macro()
    assert EXPECTED_KEYS.issubset(result.keys()), f"Missing keys: {EXPECTED_KEYS - result.keys()}"


def test_get_macro_vix_signal_calm(monkeypatch):
    """VIX of 15 should produce 'calm' signal."""
    import yfinance as yf

    histories = {
        "^VIX": _make_history(5, base=15.0, seed=10),
        "^TNX": _make_history(5, base=40.0, seed=11),
        "SPY": _make_history(250, base=500.0, seed=12),
    }

    class FakeTicker:
        def __init__(self, t):
            self._t = t

        def history(self, period="1y"):
            return histories.get(self._t, pd.DataFrame())

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    result = get_macro()
    assert result["vix_signal"] == "calm"


def test_get_macro_vix_signal_extreme_fear(monkeypatch):
    """VIX of 35 should produce 'extreme_fear' signal."""
    import yfinance as yf

    histories = {
        "^VIX": _make_history(5, base=35.0, seed=20),
        "^TNX": _make_history(5, base=40.0, seed=21),
        "SPY": _make_history(250, base=500.0, seed=22),
    }

    class FakeTicker:
        def __init__(self, t):
            self._t = t

        def history(self, period="1y"):
            return histories.get(self._t, pd.DataFrame())

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    result = get_macro()
    assert result["vix_signal"] == "extreme_fear"


def test_get_macro_handles_empty_data(monkeypatch):
    """If yfinance returns empty DataFrames, get_macro should not crash."""
    import yfinance as yf

    class FakeTicker:
        def __init__(self, t):
            pass

        def history(self, period="1y"):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    result = get_macro()
    # Should not raise; regime fields will be 'unavailable' or 'neutral'
    assert "regime" in result or "error" in result


def test_get_macro_regime_risk_on(monkeypatch):
    """SPY uptrend + calm VIX should produce 'risk_on' regime."""
    import yfinance as yf

    # SPY in clear uptrend: monotonically rising
    n = 250
    spy_prices = [400.0 + i * 0.5 for i in range(n)]
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    spy_df = pd.DataFrame(
        {
            "Close": spy_prices,
            "High": [p * 1.001 for p in spy_prices],
            "Low": [p * 0.999 for p in spy_prices],
            "Volume": [1_000_000] * n,
        },
        index=idx,
    )

    histories = {
        "^VIX": _make_history(5, base=14.0, seed=30),
        "^TNX": _make_history(5, base=40.0, seed=31),
        "SPY": spy_df,
    }

    class FakeTicker:
        def __init__(self, t):
            self._t = t

        def history(self, period="1y"):
            return histories.get(self._t, pd.DataFrame())

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    result = get_macro()
    assert result["regime"] == "risk_on"
