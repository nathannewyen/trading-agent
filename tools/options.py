"""Options market data via yfinance: implied volatility, put/call ratio, open interest."""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def _compute_max_pain(calls, puts) -> float | None:
    """Calculate the max pain strike — the strike at which combined OI loss is maximised.

    For each candidate strike, compute the total dollar pain inflicted on all call holders
    (if price expires at that strike) plus all put holders.  The strike that maximises
    total OI pain is the max pain price.

    Returns None if data is insufficient.
    """
    try:
        all_strikes = set(calls["strike"].tolist()) | set(puts["strike"].tolist())
        if not all_strikes:
            return None

        min_pain = float("inf")
        max_pain_strike = None

        for strike in sorted(all_strikes):
            # Call pain: call holders lose when price < strike
            call_pain = float(
                (calls[calls["strike"] > strike]["openInterest"].fillna(0)
                 * (calls[calls["strike"] > strike]["strike"] - strike)).sum()
            )
            # Put pain: put holders lose when price > strike
            put_pain = float(
                (puts[puts["strike"] < strike]["openInterest"].fillna(0)
                 * (strike - puts[puts["strike"] < strike]["strike"])).sum()
            )
            total_pain = call_pain + put_pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike

        return float(max_pain_strike) if max_pain_strike is not None else None
    except Exception as exc:
        logger.debug(f"max_pain calculation failed: {exc}")
        return None


def get_options_data(ticker: str) -> dict:
    ticker = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options

        if not expirations:
            return {
                "ticker": ticker,
                "error": "No options data available",
                "put_call_ratio": None,
                "atm_implied_volatility_pct": None,
                "total_call_volume": 0,
                "total_put_volume": 0,
                "call_open_interest": 0,
                "put_open_interest": 0,
                "max_pain": None,
            }

        current_price = (
            stock.info.get("currentPrice") or stock.info.get("regularMarketPrice") or 0
        )

        # Aggregate across nearest 3 expirations for more robust put/call ratio
        agg = {"call_volume": 0, "put_volume": 0, "call_oi": 0, "put_oi": 0}
        atm_iv = None
        max_pain_price = None

        for i, exp in enumerate(expirations[:3]):
            try:
                chain = stock.option_chain(exp)
                calls, puts = chain.calls, chain.puts

                if calls.empty and puts.empty:
                    logger.debug(f"Empty options chain for {ticker} exp {exp}")
                    continue

                agg["call_volume"] += int(calls["volume"].fillna(0).sum())
                agg["put_volume"] += int(puts["volume"].fillna(0).sum())
                agg["call_oi"] += int(calls["openInterest"].fillna(0).sum())
                agg["put_oi"] += int(puts["openInterest"].fillna(0).sum())

                # ATM IV from nearest expiration only
                if atm_iv is None and current_price and not calls.empty:
                    calls_copy = calls.copy()
                    calls_copy["dist"] = (calls_copy["strike"] - current_price).abs()
                    atm_row = calls_copy.nsmallest(1, "dist").iloc[0]
                    raw_iv = atm_row.get("impliedVolatility")
                    if raw_iv and raw_iv == raw_iv:  # not NaN
                        atm_iv = round(float(raw_iv) * 100, 2)

                # Max pain from nearest expiration only
                if i == 0 and not calls.empty and not puts.empty:
                    max_pain_price = _compute_max_pain(calls, puts)

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
            "max_pain": round(max_pain_price, 2) if max_pain_price is not None else None,
        }

    except Exception as exc:
        logger.error(f"Error fetching options for {ticker}: {exc}")
        return {
            "ticker": ticker,
            "error": str(exc),
            "put_call_ratio": None,
            "atm_implied_volatility_pct": None,
            "total_call_volume": 0,
            "total_put_volume": 0,
            "call_open_interest": 0,
            "put_open_interest": 0,
            "max_pain": None,
        }
