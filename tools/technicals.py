"""Technical indicators computed from yfinance historical price data."""

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def get_technicals(ticker: str, period: str = "1y") -> dict:
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)

        if hist.empty:
            return {"error": f"No price history for {ticker}", "ticker": ticker}

        close = hist["Close"]
        volume = hist["Volume"]
        current = float(close.iloc[-1])

        # RSI(14) — guard against zero avg_loss (sustained rally edge case)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        last_loss = float(loss.iloc[-1])
        if last_loss == 0:
            rsi = 100.0
        else:
            rs = gain / loss
            rsi = float((100 - 100 / (1 + rs)).iloc[-1])
        rsi = max(0.0, min(100.0, rsi))

        # MACD(12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        # Moving averages
        sma_50 = float(close.rolling(50).mean().iloc[-1])
        sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
        ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])

        # 52-week range
        high_52w = float(hist["High"].max())
        low_52w = float(hist["Low"].min())

        return {
            "ticker": ticker.upper(),
            "current_price": round(current, 2),
            "rsi_14": round(rsi, 2),
            "rsi_signal": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral",
            "macd": round(float(macd_line.iloc[-1]), 4),
            "macd_signal": round(float(signal_line.iloc[-1]), 4),
            "macd_histogram": round(float(histogram.iloc[-1]), 4),
            "macd_crossover": "bullish" if float(histogram.iloc[-1]) > 0 else "bearish",
            "sma_50": round(sma_50, 2),
            "sma_200": round(sma_200, 2) if sma_200 else None,
            "ema_20": round(ema_20, 2),
            "above_50sma": current > sma_50,
            "above_200sma": current > sma_200 if sma_200 else None,
            "golden_cross": (sma_50 > sma_200) if sma_200 else None,
            "52w_high": round(high_52w, 2),
            "52w_low": round(low_52w, 2),
            "pct_from_52w_high": round((current / high_52w - 1) * 100, 2),
            "pct_from_52w_low": round((current / low_52w - 1) * 100, 2),
            "avg_volume_30d": int(volume.rolling(30).mean().iloc[-1]),
            "volume_ratio": round(float(volume.iloc[-1]) / float(volume.rolling(30).mean().iloc[-1]), 2),
        }

    except Exception as exc:
        logger.error(f"Error computing technicals for {ticker}: {exc}")
        return {"error": str(exc), "ticker": ticker}
