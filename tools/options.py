"""Options market data via yfinance: implied volatility, put/call ratio, open interest."""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def get_options_data(ticker: str) -> dict:
    ticker = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            return {"error": "No options data available", "ticker": ticker}

        current_price = (
            stock.info.get("currentPrice") or stock.info.get("regularMarketPrice") or 0
        )

        # Aggregate across nearest 3 expirations for more robust put/call ratio
        agg = {"call_volume": 0, "put_volume": 0, "call_oi": 0, "put_oi": 0}
        atm_iv = None

        for exp in expirations[:3]:
            try:
                chain = stock.option_chain(exp)
                calls, puts = chain.calls, chain.puts

                agg["call_volume"] += int(calls["volume"].fillna(0).sum())
                agg["put_volume"] += int(puts["volume"].fillna(0).sum())
                agg["call_oi"] += int(calls["openInterest"].fillna(0).sum())
                agg["put_oi"] += int(puts["openInterest"].fillna(0).sum())

                # ATM IV from nearest expiration only
                if atm_iv is None and current_price and not calls.empty:
                    calls = calls.copy()
                    calls["dist"] = (calls["strike"] - current_price).abs()
                    atm_row = calls.nsmallest(1, "dist").iloc[0]
                    raw_iv = atm_row.get("impliedVolatility")
                    if raw_iv and raw_iv == raw_iv:  # not NaN
                        atm_iv = round(float(raw_iv) * 100, 2)
            except Exception:
                continue

        pc_ratio = (
            round(agg["put_volume"] / agg["call_volume"], 3)
            if agg["call_volume"] > 0
            else None
        )

        return {
            "ticker": ticker,
            "nearest_expiration": expirations[0],
            "expirations_available": len(expirations),
            "put_call_ratio": pc_ratio,
            "put_call_signal": (
                "bearish" if pc_ratio and pc_ratio > 1.2
                else "bullish" if pc_ratio and pc_ratio < 0.7
                else "neutral"
            ),
            "atm_implied_volatility_pct": atm_iv,
            "total_call_volume": agg["call_volume"],
            "total_put_volume": agg["put_volume"],
            "call_open_interest": agg["call_oi"],
            "put_open_interest": agg["put_oi"],
        }

    except Exception as exc:
        logger.error(f"Error fetching options for {ticker}: {exc}")
        return {"error": str(exc), "ticker": ticker}
