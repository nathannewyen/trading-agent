"""Unit tests for watchlist.py — calendar integration and file reading."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from watchlist import _load_tickers_from_file, _days_color


# --- _load_tickers_from_file ---

def test_load_tickers_basic(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text("NVDA\nAAPL\nMSFT\n")
    result = _load_tickers_from_file(str(f))
    assert result == ["NVDA", "AAPL", "MSFT"]


def test_load_tickers_skips_blank_lines(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text("NVDA\n\nAAPL\n   \nMSFT\n")
    result = _load_tickers_from_file(str(f))
    assert result == ["NVDA", "AAPL", "MSFT"]


def test_load_tickers_skips_comments(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text("# my watchlist\nNVDA\n# skip this\nAAPL\n")
    result = _load_tickers_from_file(str(f))
    assert result == ["NVDA", "AAPL"]


def test_load_tickers_uppercases(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text("nvda\naapl\n")
    result = _load_tickers_from_file(str(f))
    assert result == ["NVDA", "AAPL"]


def test_load_tickers_empty_file(tmp_path):
    f = tmp_path / "tickers.txt"
    f.write_text("")
    result = _load_tickers_from_file(str(f))
    assert result == []


# --- _days_color ---

def test_days_color_red():
    assert _days_color(1) == "red"
    assert _days_color(7) == "red"


def test_days_color_yellow():
    assert _days_color(8) == "yellow"
    assert _days_color(14) == "yellow"


def test_days_color_green():
    assert _days_color(15) == "green"
    assert _days_color(30) == "green"


# --- Calendar integration (monkeypatched) ---

def test_watchlist_calendar_integration(monkeypatch):
    """Verify that get_earnings_calendar is called with tickers from the file."""
    import yfinance as yf

    now = pd.Timestamp.now(tz="UTC")
    fake_df = pd.DataFrame(
        {"EPS Estimate": [1.0], "Reported EPS": [None]},
        index=pd.DatetimeIndex([now + pd.Timedelta(days=5)]),
    )

    class FakeTicker:
        @property
        def earnings_dates(self):
            return fake_df

    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())

    from tools.calendar import get_earnings_calendar

    result = get_earnings_calendar(["NVDA"], days_ahead=14)
    assert len(result) == 1
    assert result[0]["ticker"] == "NVDA"
    assert result[0]["days_until"] <= 14


def test_load_tickers_strips_whitespace(tmp_path):
    """Leading/trailing whitespace around ticker symbols should be stripped."""
    f = tmp_path / "tickers.txt"
    f.write_text("  NVDA  \n  AAPL\nMSFT  \n")
    result = _load_tickers_from_file(str(f))
    assert result == ["NVDA", "AAPL", "MSFT"]


def test_days_color_boundary_exactly_7():
    """Exactly 7 days should be red (urgent)."""
    assert _days_color(7) == "red"


def test_days_color_boundary_exactly_8():
    """Exactly 8 days should be yellow (upcoming)."""
    assert _days_color(8) == "yellow"
