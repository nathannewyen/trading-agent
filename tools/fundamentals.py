"""Fundamental financial ratios beyond what get_earnings provides.

Fetches balance-sheet-derived metrics: debt/equity, current ratio,
return on equity, price/book, and free cash flow yield.
"""

import logging

import yfinance as yf

from tools import cache

logger = logging.getLogger(__name__)


def get_fundamentals(ticker: str) -> dict:
    """Return key balance-sheet and valuation ratios for *ticker*."""
    cached = cache.get("fundamentals", ttl=3600, ticker=ticker)
    if cached is not None:
        return cached

    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:
        logger.error(f"yfinance info fetch failed for {ticker}: {exc}")
        return {"error": str(exc), "ticker": ticker}

    def _safe(key: str, default=None):
        val = info.get(key)
        return default if val is None else val

    market_cap = _safe("marketCap")
    free_cashflow = _safe("freeCashflow")
    fcf_yield = None
    if market_cap and free_cashflow and market_cap > 0:
        fcf_yield = round(free_cashflow / market_cap * 100, 2)

    result = {
        "ticker": ticker.upper(),
        "market_cap": market_cap,
        "enterprise_value": _safe("enterpriseValue"),
        "price_to_book": _safe("priceToBook"),
        "price_to_sales_ttm": _safe("priceToSalesTrailing12Months"),
        "debt_to_equity": _safe("debtToEquity"),
        "current_ratio": _safe("currentRatio"),
        "return_on_equity": _safe("returnOnEquity"),
        "return_on_assets": _safe("returnOnAssets"),
        "free_cashflow": free_cashflow,
        "fcf_yield_pct": fcf_yield,
        "operating_margins": _safe("operatingMargins"),
        "gross_margins": _safe("grossMargins"),
        "revenue_growth": _safe("revenueGrowth"),
        "earnings_growth": _safe("earningsGrowth"),
    }

    cache.set("fundamentals", result, ticker=ticker)
    return result
