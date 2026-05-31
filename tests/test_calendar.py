"""Unit tests for tools/calendar.py — earnings calendar and surprise history."""

import sys
from pathlib import Path
import pandas as pd
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.calendar import get_earnings_calendar, get_earnings_surprise_history


def _make_future_dates(n: int = 5, start_days: int = 7) -> pd.DataFrame:
    """Build a fake earnings_dates DataFrame with future dates."""
    now = pd.Timestamp.now(tz="UTC")
    dates = [now + pd.Timedelta(days=start_days + i * 90) for i in range(n)]
    return pd.DataFrame(
        {
            "EPS Estimate": [0.50 + i * 0.05 for i in range(n)],
            "Reported EPS": [None] * n,
        },
        index=pd.DatetimeIndex(dates),
    )


def _make_past_dates(n: int = 4) -> pd.DataFrame:
    """Build a fake earnings_dates DataFrame with past dates for surprise history."""
    now = pd.Timestamp.now(tz="UTC")
    dates = [now - pd.Timedelta(days=90 * (i + 1)) for i in range(n)]
    estimated = [1.00, 0.90, 0.80, 0.75]
    actual = [1.10, 0.85, 0.82, 0.70]
    return pd.DataFrame(
        {
            "EPS Estimate": estimated,
            "Reported EPS": actual,
        },
        index=pd.DatetimeIndex(dates),
    )


def test_get_earnings_calendar_returns_upcoming(monkeypatch):
    import yfinance as yf

    fake_df = _make_future_dates(n=3, start_days=5)

    class FakeTicker:
        @property
        def earnings_dates(self):
            return fake_df

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_earnings_calendar(["FAKE"], days_ahead=30)
    assert len(result) == 1
    assert result[0]["ticker"] == "FAKE"
    assert result[0]["days_until"] >= 0


def test_get_earnings_calendar_excludes_beyond_window(monkeypatch):
    import yfinance as yf

    # All dates are 60+ days away; window is 30 days — should return nothing
    fake_df = _make_future_dates(n=3, start_days=61)

    class FakeTicker:
        @property
        def earnings_dates(self):
            return fake_df

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_earnings_calendar(["FAKE"], days_ahead=30)
    assert result == []


def test_get_earnings_calendar_sorted_by_days(monkeypatch):
    import yfinance as yf

    # Two tickers with different distances
    now = pd.Timestamp.now(tz="UTC")
    df_a = pd.DataFrame(
        {"EPS Estimate": [1.0], "Reported EPS": [None]},
        index=pd.DatetimeIndex([now + pd.Timedelta(days=5)]),
    )
    df_b = pd.DataFrame(
        {"EPS Estimate": [1.0], "Reported EPS": [None]},
        index=pd.DatetimeIndex([now + pd.Timedelta(days=12)]),
    )

    call_count = [0]
    tickers = ["ALPHA", "BETA"]
    dfs = [df_a, df_b]

    class FakeTicker:
        def __init__(self, t):
            self._idx = tickers.index(t) if t in tickers else 0

        @property
        def earnings_dates(self):
            return dfs[self._idx]

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    result = get_earnings_calendar(["ALPHA", "BETA"], days_ahead=30)
    assert len(result) == 2
    assert result[0]["days_until"] <= result[1]["days_until"]


def test_get_earnings_surprise_history(monkeypatch):
    import yfinance as yf

    fake_df = _make_past_dates(n=4)

    class FakeTicker:
        @property
        def earnings_dates(self):
            return fake_df

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_earnings_surprise_history("FAKE", quarters=4)
    assert len(result) == 4
    for entry in result:
        assert "date" in entry
        assert "estimated_eps" in entry
        assert "actual_eps" in entry
        assert "surprise_pct" in entry


def test_get_earnings_surprise_beat_miss(monkeypatch):
    import yfinance as yf

    # First entry: beat (actual > estimate); second: miss
    now = pd.Timestamp.now(tz="UTC")
    fake_df = pd.DataFrame(
        {
            "EPS Estimate": [1.00, 1.00],
            "Reported EPS": [1.10, 0.90],
        },
        index=pd.DatetimeIndex([now - pd.Timedelta(days=90), now - pd.Timedelta(days=180)]),
    )

    class FakeTicker:
        @property
        def earnings_dates(self):
            return fake_df

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_earnings_surprise_history("FAKE", quarters=2)
    assert result[0]["surprise_pct"] > 0   # beat
    assert result[1]["surprise_pct"] < 0   # miss


def test_get_earnings_surprise_empty_on_error(monkeypatch):
    import yfinance as yf

    class FakeTicker:
        @property
        def earnings_dates(self):
            raise RuntimeError("API down")

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    result = get_earnings_surprise_history("FAKE")
    assert result == []
