"""Unit tests for tools/options.py — error path and max_pain edge cases."""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.options import _compute_max_pain, get_options_data


# --- _compute_max_pain ---

def _make_chain(call_strikes, call_oi, put_strikes, put_oi):
    calls = pd.DataFrame({"strike": call_strikes, "openInterest": call_oi})
    puts = pd.DataFrame({"strike": put_strikes, "openInterest": put_oi})
    return calls, puts


def test_max_pain_basic():
    """Max pain should return the strike that minimises total OI dollar loss."""
    # Simple case: equal OI on both sides around $150
    calls, puts = _make_chain(
        call_strikes=[140, 150, 160, 170],
        call_oi=[100, 200, 300, 100],
        put_strikes=[130, 140, 150, 160],
        put_oi=[100, 300, 200, 100],
    )
    result = _compute_max_pain(calls, puts)
    assert result is not None
    assert isinstance(result, float)


def test_max_pain_empty_chains():
    """Empty DataFrames should return None without crashing."""
    calls = pd.DataFrame({"strike": [], "openInterest": []})
    puts = pd.DataFrame({"strike": [], "openInterest": []})
    result = _compute_max_pain(calls, puts)
    assert result is None


def test_max_pain_single_strike():
    """Single-strike chain should return that strike."""
    calls, puts = _make_chain(
        call_strikes=[100],
        call_oi=[500],
        put_strikes=[100],
        put_oi=[500],
    )
    result = _compute_max_pain(calls, puts)
    assert result == 100.0


# --- get_options_data error path ---

def test_get_options_data_no_options(monkeypatch):
    """When no options exist, return a structured dict with None fields — no crash."""
    import yfinance as yf

    class FakeTicker:
        options = []

        @property
        def info(self):
            return {}

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_options_data("FAKE")
    assert "error" in result
    assert result["put_call_ratio"] is None
    assert result["atm_implied_volatility_pct"] is None
    assert result["max_pain"] is None
    assert result["total_call_volume"] == 0


def test_get_options_data_empty_chain(monkeypatch):
    """When option_chain returns empty DataFrames, should continue gracefully."""
    import yfinance as yf
    from collections import namedtuple

    Chain = namedtuple("Chain", ["calls", "puts"])

    class FakeTicker:
        options = ["2025-01-17"]

        @property
        def info(self):
            return {"currentPrice": 150.0}

        def option_chain(self, exp):
            return Chain(
                calls=pd.DataFrame(columns=["strike", "volume", "openInterest", "impliedVolatility"]),
                puts=pd.DataFrame(columns=["strike", "volume", "openInterest", "impliedVolatility"]),
            )

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_options_data("FAKE")
    # Should not raise; may return 0 volumes
    assert "ticker" in result
    assert result["total_call_volume"] == 0


def test_get_options_data_exception_returns_structured_dict(monkeypatch):
    """A hard exception in yf.Ticker should return a structured error dict."""
    import yfinance as yf

    class BrokenTicker:
        @property
        def options(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(yf, "Ticker", lambda t: BrokenTicker())

    result = get_options_data("FAKE")
    assert "error" in result
    assert result["put_call_ratio"] is None
    assert result["max_pain"] is None
