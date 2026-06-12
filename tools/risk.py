"""Risk metrics: beta, annualised volatility, max drawdown, Sharpe ratio, correlation to SPY."""

import logging
import math

import yfinance as yf

from tools import cache

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.05   # approximate annualised risk-free rate
TRADING_DAYS = 252


def get_risk_metrics(ticker: str, period: str = "1y") -> dict:
    """Compute risk metrics for *ticker* over the given history period."""
    cached = cache.get("risk", ttl=900, ticker=ticker, period=period)
    if cached is not None:
        return cached

    try:
        stock = yf.download(ticker, period=period, progress=False, auto_adjust=True, timeout=15)
        spy = yf.download("SPY", period=period, progress=False, auto_adjust=True, timeout=15)
    except Exception as exc:
        logger.error(f"yfinance download failed for {ticker}: {exc}")
        return {"error": str(exc), "ticker": ticker}

    if stock.empty or spy.empty:
        return {"error": "No price data returned", "ticker": ticker}

    stock_ret = stock["Close"].pct_change().dropna()
    spy_ret = spy["Close"].pct_change().dropna()

    # Align on common dates
    common = stock_ret.index.intersection(spy_ret.index)
    if len(common) < 20:
        return {"error": "Insufficient overlapping data", "ticker": ticker}

    sr = stock_ret.loc[common]
    mr = spy_ret.loc[common]

    # Annualised volatility
    ann_vol = float(sr.std() * math.sqrt(TRADING_DAYS))

    # Beta
    cov = float(sr.cov(mr))
    spy_var = float(mr.var())
    beta = round(cov / spy_var, 3) if spy_var else None

    # Sharpe ratio (annualised)
    excess = sr.mean() * TRADING_DAYS - RISK_FREE_RATE
    sharpe = round(excess / ann_vol, 3) if ann_vol else None

    # Max drawdown
    cumulative = (1 + sr).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = round(float(drawdown.min()), 4)

    # Correlation to SPY
    correlation = round(float(sr.corr(mr)), 3)

    result = {
        "ticker": ticker.upper(),
        "period": period,
        "beta": beta,
        "annualised_volatility_pct": round(ann_vol * 100, 2),
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "spy_correlation": correlation,
        "data_points": len(common),
    }

    cache.set("risk", result, ticker=ticker, period=period)
    return result


def get_var(ticker: str, confidence: float = 0.95, period: str = "1y") -> dict:
    """Compute historical Value-at-Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall).

    Args:
        ticker: Stock symbol.
        confidence: Confidence level, e.g. 0.95 for 95% VaR.
        period: History period for daily return distribution.

    Returns:
        dict with var_pct (1-day VaR as % of position) and cvar_pct (expected shortfall).
    """
    try:
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    except Exception as exc:
        return {"error": str(exc), "ticker": ticker}

    if data.empty:
        return {"error": "No price data", "ticker": ticker}

    rets = data["Close"].squeeze().pct_change().dropna().sort_values()
    cutoff = int((1 - confidence) * len(rets))
    if cutoff < 1:
        return {"error": "Not enough data for VaR at this confidence level", "ticker": ticker}

    var = float(rets.iloc[cutoff])
    cvar = float(rets.iloc[:cutoff].mean())

    return {
        "ticker": ticker.upper(),
        "confidence_pct": round(confidence * 100, 1),
        "var_1d_pct": round(var * 100, 3),
        "cvar_1d_pct": round(cvar * 100, 3),
        "interpretation": (
            f"On 95% of trading days, the single-day loss is no worse than {abs(var*100):.2f}%. "
            f"On the worst {100-confidence*100:.0f}% of days, the average loss is {abs(cvar*100):.2f}%."
        ),
    }
