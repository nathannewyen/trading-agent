"""Technical indicators computed from yfinance historical price data."""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def _compute_rsi(close, period: int = 14) -> float:
    """Compute RSI for a price series. Returns a value in [0, 100].

    Handles the edge case where average loss is zero (sustained rally),
    which would produce a division-by-zero without the guard.
    """
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    last_loss = float(loss.iloc[-1])
    if last_loss == 0:
        return 100.0
    rs = gain / loss
    rsi = float((100 - 100 / (1 + rs)).iloc[-1])
    return max(0.0, min(100.0, rsi))


def get_technicals(ticker: str, period: str = "1y") -> dict:
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)

        if hist.empty:
            return {"error": f"No price history for {ticker}", "ticker": ticker}

        close = hist["Close"]
        volume = hist["Volume"]
        current = float(close.iloc[-1])
        n = len(close)

        # RSI(14) — delegated to private helper
        rsi = _compute_rsi(close, period=14)

        # MACD(12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        # Moving averages — graceful fallback when history is short
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if n >= 50 else None
        sma_200 = float(close.rolling(200).mean().iloc[-1]) if n >= 200 else None
        ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])

        # 52-week range
        high_52w = float(hist["High"].max())
        low_52w = float(hist["Low"].min())

        # Bollinger Bands (20-period, 2 std)
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        bb_width = float((bb_upper - bb_lower).iloc[-1]) if n >= 20 else None
        bb_pct = (
            float((current - float(bb_lower.iloc[-1])) / float(bb_upper.iloc[-1] - bb_lower.iloc[-1]))
            if n >= 20 and float(bb_upper.iloc[-1] - bb_lower.iloc[-1]) > 0
            else None
        )

        # Volume spike: today's volume > 2x 30-day average
        avg_vol_30 = float(volume.rolling(30).mean().iloc[-1]) if n >= 30 else None
        today_vol = float(volume.iloc[-1])
        volume_spike = bool(today_vol > 2 * avg_vol_30) if avg_vol_30 else False

        return {
            "ticker": ticker.upper(),
            "current_price": round(current, 2),
            "rsi_14": round(rsi, 2),
            "rsi_signal": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral",
            "macd": round(float(macd_line.iloc[-1]), 4),
            "macd_signal": round(float(signal_line.iloc[-1]), 4),
            "macd_histogram": round(float(histogram.iloc[-1]), 4),
            "macd_crossover": "bullish" if float(histogram.iloc[-1]) > 0 else "bearish",
            "sma_50": round(sma_50, 2) if sma_50 is not None else None,
            "sma_200": round(sma_200, 2) if sma_200 is not None else None,
            "ema_20": round(ema_20, 2),
            "above_50sma": (current > sma_50) if sma_50 is not None else None,
            "above_200sma": (current > sma_200) if sma_200 is not None else None,
            "golden_cross": (sma_50 > sma_200) if (sma_50 is not None and sma_200 is not None) else None,
            "bb_upper": round(float(bb_upper.iloc[-1]), 2) if n >= 20 else None,
            "bb_mid": round(float(bb_mid.iloc[-1]), 2) if n >= 20 else None,
            "bb_lower": round(float(bb_lower.iloc[-1]), 2) if n >= 20 else None,
            "bb_width": round(bb_width, 2) if bb_width is not None else None,
            "bb_pct_b": round(bb_pct, 3) if bb_pct is not None else None,
            "52w_high": round(high_52w, 2),
            "52w_low": round(low_52w, 2),
            "pct_from_52w_high": round((current / high_52w - 1) * 100, 2),
            "pct_from_52w_low": round((current / low_52w - 1) * 100, 2),
            "avg_volume_30d": int(avg_vol_30) if avg_vol_30 is not None else None,
            "volume_ratio": round(today_vol / avg_vol_30, 2) if avg_vol_30 else None,
            "volume_spike": volume_spike,
        }

    except Exception as exc:
        logger.error(f"Error computing technicals for {ticker}: {exc}")
        return {"error": str(exc), "ticker": ticker}
