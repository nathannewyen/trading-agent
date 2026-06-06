# Contributing

## Setup

```bash
git clone https://github.com/your-org/trading-agent.git
cd trading-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env
```

## Development

All research logic lives in `tools/`. Add a new data source by:
1. Creating `tools/my_source.py` with a `get_my_source(ticker)` function
2. Registering it in the `TOOLS` list in `agent.py`
3. Adding dispatch logic in `_dispatch_tool()` in `agent.py`

Use `make research TICKER=NVDA` for quick iteration.

## Testing

```bash
make test            # run all tests
python -m pytest tests/test_calculator.py -v   # single file
```

Tests use `monkeypatch` to stub `yfinance.Ticker` — no live network calls required.

## Evals

```bash
make evals           # 5-case smoke test (no BRAINTRUST_API_KEY needed for scorer tests)
python -m pytest evals/test_scorers.py -v   # test the eval scorers themselves
```

## Pull Request Process

1. Branch off `main`: `git checkout -b feat/my-feature`
2. Write code and tests (aim for each new function to have at least one test)
3. Run `make test` and `make lint` before pushing
4. Open a PR against `main` — CI will run `pytest tests/` automatically
5. One approval required before merge

## Code style

- Line length: 100 characters (ruff enforced)
- Type hints on all public functions
- Docstrings on all modules and public functions
- No bare `except:` — always catch a specific exception type
