"""Macro market context: VIX, 10-year Treasury yield, and SPY trend.

Fetches three key regime indicators from yfinance:
  - ^VIX  — CBOE Volatility Index (fear gauge)
  - ^TNX  — 10-year Treasury yield
  - SPY   — S&P 500 ETF (SMA trend proxy)

The agent calls this first (step 0) to understand whether the market is in a
risk-on or risk-off regime before forming a single-stock thesis.
"""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)

_TICKERS = {
    "vix": "^VIX",
    "ten_year_yield": "^TNX",
    "spy": "SPY",
}


def get_macro() -> dict:
    """Return current VIX, 10-year yield, and SPY trend context."""
    try:
        result: dict = {}

        # VIX
        vix_data = yf.Ticker(_TICKERS["vix"]).history(period="5d")
        if not vix_data.empty:
            vix_val = round(float(vix_data["Close"].iloc[-1]), 2)
            result["vix"] = vix_val
            result["vix_signal"] = (
                "extreme_fear" if vix_val > 30
                else "elevated_fear" if vix_val > 20
                else "calm"
            )
        else:
            result["vix"] = None
            result["vix_signal"] = "unavailable"

        # 10-year Treasury yield (^TNX quotes in tenths of a percent)
        tnx_data = yf.Ticker(_TICKERS["ten_year_yield"]).history(period="5d")
        if not tnx_data.empty:
            tnx_val = round(float(tnx_data["Close"].iloc[-1]), 3)
            result["ten_year_yield_pct"] = tnx_val
            result["yield_signal"] = (
                "high" if tnx_val > 4.5
                else "moderate" if tnx_val > 3.5
                else "low"
            )
        else:
            result["ten_year_yield_pct"] = None
            result["yield_signal"] = "unavailable"

        # SPY trend: compare current price to 50-day and 200-day SMAs
        spy_hist = yf.Ticker(_TICKERS["spy"]).history(period="1y")
        if not spy_hist.empty:
            spy_close = spy_hist["Close"]
            spy_current = round(float(spy_close.iloc[-1]), 2)
            sma50 = float(spy_close.rolling(50).mean().iloc[-1]) if len(spy_close) >= 50 else None
            sma200 = float(spy_close.rolling(200).mean().iloc[-1]) if len(spy_close) >= 200 else None

            result["spy_price"] = spy_current
            result["spy_sma50"] = round(sma50, 2) if sma50 else None
            result["spy_sma200"] = round(sma200, 2) if sma200 else None
            result["spy_above_50sma"] = (spy_current > sma50) if sma50 else None
            result["spy_above_200sma"] = (spy_current > sma200) if sma200 else None
            result["spy_trend"] = (
                "uptrend" if (sma50 and sma200 and spy_current > sma50 > sma200)
                else "downtrend" if (sma50 and sma200 and spy_current < sma50 < sma200)
                else "mixed"
            )
        else:
            result["spy_price"] = None
            result["spy_trend"] = "unavailable"

        # Composite regime label
        vix_ok = result.get("vix") is not None
        spy_trend = result.get("spy_trend", "mixed")
        vix_sig = result.get("vix_signal", "calm")

        if spy_trend == "uptrend" and vix_sig == "calm":
            result["regime"] = "risk_on"
        elif spy_trend == "downtrend" or vix_sig in ("extreme_fear", "elevated_fear"):
            result["regime"] = "risk_off"
        else:
            result["regime"] = "neutral"

        return result

    except Exception as exc:
        logger.error(f"Error fetching macro data: {exc}")
        return {"error": str(exc)}
