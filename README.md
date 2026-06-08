# Trading Research Agent

[![Tests](https://github.com/your-org/trading-agent/actions/workflows/test.yml/badge.svg)](https://github.com/your-org/trading-agent/actions/workflows/test.yml)

An agentic research pipeline built on the Anthropic API that fetches earnings data, scrapes recent news, computes technical indicators, checks macro regime context, and synthesizes a structured trade thesis — with an optional critic agent that stress-tests the output.

## Features

| Feature | Description |
|---------|-------------|
| **6 research tools** | Earnings (yfinance), web search (DuckDuckGo), technicals (RSI/MACD/Bollinger/SMA), options (IV/P-C ratio/max pain), calculator, macro (VIX/yields/SPY) |
| **Macro context** | `get_macro` fetches VIX, 10-year yield, SPY trend — establishes market regime before single-stock research |
| **Tool-use loop** | Anthropic tool_use with retry logic (exponential backoff) and context window management |
| **Disk cache** | Atomic TTL-based JSON cache — avoids re-fetching the same ticker within a session |
| **Two-agent critic** | Researcher → Critic pattern; critic challenges claims, flags overconfidence, extracts composite confidence score |
| **Portfolio mode** | Research + rank multiple tickers; `--top-n`, `--csv`, sector breakdown |
| **Comparison mode** | Side-by-side analysis of two stocks with `--quick` flag for fast earnings-only view |
| **Earnings calendar** | Upcoming earnings dates with beat/miss history, color-coded by days away |
| **Watchlist mode** | `--watchlist-file` reads tickers from a text file; `--watch` for continuous refresh |
| **Sector prompts** | `--sector tech/energy/financials/healthcare/consumer` for specialized analysis |
| **News aggregation** | Multi-query deduplication across 3 search templates with per-article sentiment |
| **Fundamentals tool** | Balance-sheet ratios: P/B, P/S, D/E, ROE, FCF yield via `tools/fundamentals.py` |
| **Eval suite** | Braintrust eval with 5 custom scorers across 50 test cases; `--summary` flag for quick stats |
| **CI** | GitHub Actions runs `pytest tests/` on every push and PR |
| **Rich CLI** | Colored output, spinner progress, formatted markdown in terminal |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add ANTHROPIC_API_KEY (and BRAINTRUST_API_KEY if running evals)
```

## Usage

```bash
# Single ticker thesis
python agent.py NVDA

# With two-agent critic
python agent.py NVDA --critique

# Save to file
python agent.py TSLA --output tsla_thesis.md --critique

# Portfolio — research and rank multiple tickers
python portfolio.py NVDA AMD INTC QCOM

# Portfolio — top 2 only, export to CSV
python portfolio.py NVDA AMD INTC --top-n 2 --csv results.csv

# Side-by-side comparison
python compare.py NVDA AMD

# Quick comparison (earnings data only — faster)
python compare.py NVDA AMD --quick

# Watchlist with upcoming earnings
python watchlist.py NVDA AAPL MSFT --days 14

# Watchlist from a file
python watchlist.py --watchlist-file my_tickers.txt --days 30

# Makefile shortcuts
make research TICKER=NVDA
make test
```

## Tests

```bash
# Run all tests (40+ tests, no network calls needed)
make test

# Single module
python -m pytest tests/test_technicals.py -v
python -m pytest evals/test_scorers.py -v
```

**Test count:** 40+ unit tests across calculator, cache, sentiment, technicals, options, macro, calendar, and watchlist modules.

## Evals

```bash
# Full eval (50 cases) — requires BRAINTRUST_API_KEY
python evals/run_evals.py --tag v1

# Quick smoke test (5 cases)
python evals/run_evals.py --limit 5 --tag dev

# Print mean score per scorer
python evals/run_evals.py --limit 5 --summary

# Test the scorers themselves (no API key needed)
python -m pytest evals/test_scorers.py -v
```

**Scorers:**
- `thesis_coherence` — all 6 required sections present
- `data_grounding` — specific numbers used, not vague language
- `has_recommendation` — actionable rec with bias / entry / target / stop
- `risk_quality` — bear case has concrete, data-backed risks (handles both `## 5. Bear Case` and `**Bear Case**`)
- `catalyst_recency` — catalysts reference recent time periods

## Architecture

```
agent.py              # Tool-use loop: 6 tools, retry, context truncation, input validation
critic.py             # Two-agent flow: researcher → critic; extracts confidence_score
portfolio.py          # Multi-ticker research + ranked table; --top-n, --csv, sector breakdown
compare.py            # Side-by-side comparison with verdict agent; --quick mode
watchlist.py          # Earnings watchlist; --watchlist-file, color-coded dates
config.py             # Centralized constants: MODEL, TOKEN_LIMITS, CACHE_TTLs
tools/
  earnings.py         # yfinance: EPS, revenue, margins, insiders, institutions
  technicals.py       # RSI(14), MACD(12,26,9), Bollinger(20,2), SMA(50/200), volume spike
  options.py          # Put/call ratio, ATM IV, open interest, max pain
  search.py           # DuckDuckGo search with per-headline + aggregate sentiment
  calculator.py       # Safe math eval (restricted namespace)
  cache.py            # Atomic TTL-based JSON disk cache (.cache/ dir); stats()
  calendar.py         # Upcoming earnings dates + beat/miss surprise history
  macro.py            # VIX, 10-year yield, SPY trend — market regime context
prompts/
  system.py           # Researcher system prompt (step 0: get_macro)
  critic.py           # Critic agent system prompt
  compare.py          # Comparison agent system prompt
  earnings_preview.py # Pre-earnings watchlist research prompt
evals/
  run_evals.py        # Braintrust eval — 5 scorers; --summary flag
  test_scorers.py     # Unit tests for all 5 scorers
  dataset.json        # 50 test cases across sectors
tests/
  test_calculator.py
  test_cache.py
  test_sentiment.py
  test_technicals.py
  test_options.py
  test_macro.py
  test_calendar.py
  test_watchlist.py
.github/workflows/
  test.yml            # CI: pytest tests/ on push/PR
```

## Key implementation details

- **Retry logic** — exponential backoff (5s, 10s, 20s) on rate limit and API errors
- **Context window management** — estimates token count (~4 chars/token), drops oldest message pairs when approaching 150k tokens; always preserves the original user request
- **Atomic cache writes** — writes to `.json.tmp` then renames to prevent partial reads on interruption
- **Multi-agent critic** — separate `client.messages.create` call; extracts composite `confidence_score` (0–1) from stated confidence + critic adjustment + verdict
- **Max pain calculation** — finds the strike minimising combined call+put OI dollar pain
- **Macro tool** — VIX, 10Y yield, SPY SMA50/200 trend fetched before single-stock research for regime context
- **Safe calculator** — `eval()` with a restricted namespace (no builtins, only `math` functions)
- **Volume spike detection** — flags when today's volume exceeds 2x the 30-day average
- **Bollinger Bands** — 20-period, 2 std with `%B` position indicator
- **Short history fallback** — SMA50/200 return `None` when history < 50/200 days

## Prompt evolution

| Version | Change | Notes |
|---------|--------|-------|
| v1 | Initial prompt | Baseline |
| v2 | Added technicals + options to research steps; expanded output format | +Technical Setup section |
| v3 | Added step 0: call get_macro for market regime context | +Macro tool |
