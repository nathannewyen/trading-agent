# Trading Research Agent

An agentic research pipeline built on the Anthropic API that fetches earnings data, scrapes recent news, computes technical indicators, and synthesizes a structured trade thesis — with an optional critic agent that stress-tests the output.

## Features

| Feature | Description |
|---------|-------------|
| **5 research tools** | Earnings (yfinance), web search (DuckDuckGo), technicals (RSI/MACD/SMA), options (IV/P-C ratio), calculator |
| **Tool-use loop** | Anthropic tool_use with retry logic (exponential backoff) and context window management |
| **Disk cache** | TTL-based JSON cache — avoids re-fetching the same ticker within a session |
| **Two-agent critic** | Researcher → Critic pattern; critic challenges claims, flags overconfidence, suggests missing risks |
| **Portfolio mode** | Research + rank multiple tickers in one run |
| **Comparison mode** | Side-by-side analysis of two stocks with a verdict |
| **Earnings calendar** | Upcoming earnings dates for a watchlist |
| **Eval suite** | Braintrust eval with 5 custom scorers across 50 test cases |
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

# Side-by-side comparison
python compare.py NVDA AMD

# Earnings calendar (edit tickers list in script or import as module)
python -c "from tools.calendar import get_earnings_calendar; import json; print(json.dumps(get_earnings_calendar(['NVDA','AAPL','MSFT','META'], days_ahead=45), indent=2))"
```

## Evals

```bash
# Full eval (50 cases) — requires BRAINTRUST_API_KEY
python evals/run_evals.py --tag v1

# Quick smoke test (5 cases)
python evals/run_evals.py --limit 5 --tag dev

# Compare prompt versions in Braintrust UI after running v1 and v2
```

**Scorers:**
- `thesis_coherence` — all 6 required sections present
- `data_grounding` — specific numbers used, not vague language
- `has_recommendation` — actionable rec with bias / entry / target / stop
- `risk_quality` — bear case has concrete, data-backed risks
- `catalyst_recency` — catalysts reference recent time periods

## Architecture

```
agent.py              # Tool-use loop: 5 tools, retry, context truncation
critic.py             # Two-agent flow: researcher → critic
portfolio.py          # Multi-ticker research + ranked summary table
compare.py            # Side-by-side comparison with verdict agent
tools/
  earnings.py         # yfinance: EPS, revenue, margins, insiders, institutions
  technicals.py       # RSI(14), MACD(12,26,9), SMA(50/200), EMA(20), volume
  options.py          # Put/call ratio, ATM IV, open interest
  search.py           # DuckDuckGo web search with disk cache
  calculator.py       # Safe math eval (restricted namespace)
  cache.py            # TTL-based JSON disk cache (.cache/ dir)
  calendar.py         # Upcoming earnings dates for a watchlist
prompts/
  system.py           # Researcher system prompt (v1)
  critic.py           # Critic agent system prompt
evals/
  run_evals.py        # Braintrust eval — 5 scorers
  dataset.json        # 50 test cases across sectors
```

## Key implementation details

- **Retry logic** — exponential backoff (5s, 10s, 20s) on rate limit and API errors
- **Context window management** — estimates token count (~4 chars/token), drops oldest message pairs when approaching 150k tokens; always preserves the original user request
- **Disk cache** — MD5-keyed JSON files in `.cache/`, TTL 1h for earnings, 30min for search; `cache.clear_all()` for invalidation
- **Multi-agent critic** — separate `client.messages.create` call with its own system prompt and no tools; no shared state with researcher agent
- **Safe calculator** — `eval()` with a restricted namespace (no builtins, only `math` functions)
- **Portfolio scoring** — offline thesis quality score (coherence + data density + rec completeness) ranks tickers without extra API calls
- **Watchlist mode** — earnings calendar filters to near-term catalysts, then research runs with an earnings-focused prompt variant

## Prompt evolution

| Version | Change | Eval delta |
|---------|--------|------------|
| v1 | Initial prompt | baseline |
| v2 | Added technicals + options to research steps; expanded output format | +technical_setup section |

Run `python evals/run_evals.py --tag v1` and `--tag v2` then compare in the Braintrust UI.
