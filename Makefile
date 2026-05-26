.PHONY: research test evals clean lint

# Default ticker for quick runs; override with: make research TICKER=AAPL
TICKER ?= NVDA

research:
	python agent.py $(TICKER)

research-critique:
	python agent.py $(TICKER) --critique

test:
	python -m pytest tests/ -v

evals:
	python evals/run_evals.py --limit 5 --tag dev

evals-full:
	python evals/run_evals.py --tag prod

clean:
	rm -rf .cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

lint:
	python -m ruff check . --fix
