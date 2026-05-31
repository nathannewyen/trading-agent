"""Upcoming earnings calendar for a watchlist of tickers."""

import logging
from datetime import date, timezone

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def get_earnings_calendar(tickers: list[str], days_ahead: int = 30) -> list[dict]:
    """
    Return upcoming earnings dates for each ticker, sorted by soonest first.
    Filters to events within `days_ahead` days from today.
    """
    results = []
    now = pd.Timestamp.now(tz="UTC")
    cutoff = now + pd.Timedelta(days=days_ahead)

    for ticker in tickers:
        ticker = ticker.upper()
        try:
            stock = yf.Ticker(ticker)
            dates = stock.earnings_dates

            if dates is None or dates.empty:
                continue

            upcoming = dates[(dates.index > now) & (dates.index <= cutoff)]
            if upcoming.empty:
                continue

            row = upcoming.iloc[0]
            next_date = upcoming.index[0]
            days_until = (next_date.date() - date.today()).days

            results.append(
                {
                    "ticker": ticker,
                    "earnings_date": str(next_date)[:10],
                    "days_until": days_until,
                    "estimated_eps": (
                        round(float(row.get("EPS Estimate", 0) or 0), 2)
                        if row.get("EPS Estimate") == row.get("EPS Estimate")
                        else None
                    ),
                }
            )
        except Exception as exc:
            logger.debug(f"Could not fetch calendar for {ticker}: {exc}")

    return sorted(results, key=lambda x: x["days_until"])


def get_earnings_surprise_history(ticker: str, quarters: int = 4) -> list[dict]:
    """Return the last N quarters of EPS beat/miss history for a ticker.

    Each entry contains:
      - date: earnings date string
      - estimated_eps: analyst consensus estimate
      - actual_eps: reported EPS
      - surprise_pct: percentage surprise (positive = beat)

    Returns an empty list if data is unavailable.
    """
    ticker = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        dates = stock.earnings_dates

        if dates is None or dates.empty:
            return []

        now = pd.Timestamp.now(tz="UTC")
        past = dates[dates.index <= now].head(quarters)

        history = []
        for ts, row in past.iterrows():
            est = row.get("EPS Estimate")
            actual = row.get("Reported EPS")
            if est is None or actual is None:
                continue
            try:
                est_f = float(est)
                actual_f = float(actual)
            except (TypeError, ValueError):
                continue
            if est_f == 0:
                surprise_pct = 0.0
            else:
                surprise_pct = round((actual_f - est_f) / abs(est_f) * 100, 2)
            history.append(
                {
                    "date": str(ts)[:10],
                    "estimated_eps": round(est_f, 4),
                    "actual_eps": round(actual_f, 4),
                    "surprise_pct": surprise_pct,
                }
            )

        return history

    except Exception as exc:
        logger.debug(f"Could not fetch surprise history for {ticker}: {exc}")
        return []
