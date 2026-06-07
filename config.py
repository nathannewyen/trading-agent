"""Centralized configuration constants for the trading research agent.

Import these instead of defining magic numbers inline across modules.
"""

# Anthropic model
MODEL = "claude-opus-4-7"

# Token limits
MAX_OUTPUT_TOKENS = 4096
CONTEXT_TOKEN_LIMIT = 150_000

# Retry / loop control
MAX_RETRIES = 3
MAX_ITERATIONS = 12

# Cache TTLs (seconds)
CACHE_TTL_EARNINGS = 3600       # 1 hour — fundamentals change slowly
CACHE_TTL_SEARCH = 1800         # 30 min — news is more time-sensitive
CACHE_TTL_TECHNICALS = 900      # 15 min — prices update throughout the day
CACHE_TTL_OPTIONS = 600         # 10 min — options data is fast-moving
CACHE_TTL_CALENDAR = 7200       # 2 hours — earnings dates are stable

# Network timeouts (seconds)
SEARCH_TIMEOUT = 10
HTTP_TIMEOUT = 15

# Logging / output
VERBOSE = False                 # override with --verbose CLI flag
