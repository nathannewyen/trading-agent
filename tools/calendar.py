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
