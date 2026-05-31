"""Pre-earnings research prompt for the watchlist agent."""

EARNINGS_PREVIEW_PROMPT = (
    "Research {ticker} ahead of its earnings in {days_until} days. "
    "Focus on: what consensus expects, what could surprise (beat or miss), "
    "the key metrics to watch (revenue growth, margin trajectory, guidance), "
    "and whether the risk/reward favors holding through earnings. "
    "Conclude with a clear pre-earnings stance: Hold, Buy, or Reduce."
)
