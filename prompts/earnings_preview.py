"""Pre-earnings research prompt templates for the watchlist agent."""

EARNINGS_PREVIEW_PROMPT = (
    "Research {ticker} ahead of its earnings in {days_until} days. "
    "Focus on: what consensus expects, what could surprise (beat or miss), "
    "the key metrics to watch (revenue growth, margin trajectory, guidance), "
    "options market positioning (IV, put/call ratio), and whether the "
    "risk/reward favors holding through earnings. "
    "Conclude with a clear pre-earnings stance: Hold, Buy, or Reduce."
)

# Shorter variant for the --quick flag or limited context windows
EARNINGS_PREVIEW_PROMPT_SHORT = (
    "In 3-5 bullet points, summarise the key earnings expectations for {ticker} "
    "({days_until} days until earnings): consensus EPS/revenue, most likely surprise "
    "direction, options sentiment (IV/put-call), and your recommended pre-earnings "
    "stance (Hold/Buy/Reduce)."
)

# Sector-specific variant that asks for peer context
EARNINGS_PREVIEW_PROMPT_WITH_PEERS = (
    "Research {ticker} ahead of its earnings in {days_until} days. "
    "Include: consensus estimates, recent peer earnings results from the same sector "
    "that may set expectations, options market sentiment, and a pre-earnings stance "
    "(Hold/Buy/Reduce) with a stop loss level."
)
