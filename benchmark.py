"""Benchmark script for comparing sequential vs parallel portfolio research performance.

Measures wall-clock time and reports speedup factor.  Does NOT make real API calls —
uses a mock agent that sleeps for a configurable duration to simulate latency.

Usage:
    python benchmark.py --tickers NVDA AAPL MSFT TSLA --simulate-latency 2
"""

import argparse
import time
from unittest.mock import patch

from rich.console import Console
from rich.table import Table

console = Console()


def _mock_agent(ticker: str, latency: float) -> str:
    time.sleep(latency)
    return f"## Mock thesis for {ticker}\n**Bias:** Bullish\n**Confidence:** High\n**Sector:** Technology"


def benchmark(tickers: list[str], workers: int = 4, latency: float = 1.0) -> dict:
    """Run sequential and parallel benchmarks, return timing comparison."""

    # Sequential
    with patch("agent.run_agent", side_effect=lambda t, *a, **kw: _mock_agent(t, latency)):
        from portfolio import run_portfolio
        t0 = time.perf_counter()
        run_portfolio(tickers)
        sequential_secs = time.perf_counter() - t0

    # Parallel
    with patch("agent.run_agent", side_effect=lambda t, *a, **kw: _mock_agent(t, latency)):
        from async_portfolio import run_parallel_portfolio
        t0 = time.perf_counter()
        run_parallel_portfolio(tickers, workers=workers)
        parallel_secs = time.perf_counter() - t0

    speedup = sequential_secs / parallel_secs if parallel_secs > 0 else float("inf")

    return {
        "tickers": len(tickers),
        "simulated_latency_sec": latency,
        "workers": workers,
        "sequential_secs": round(sequential_secs, 2),
        "parallel_secs": round(parallel_secs, 2),
        "speedup_factor": round(speedup, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark sequential vs parallel portfolio research")
    parser.add_argument("--tickers", nargs="+", default=["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOG"],
                        help="Tickers to benchmark (default: 6 tickers)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default 4)")
    parser.add_argument("--simulate-latency", type=float, default=1.0, metavar="SEC",
                        help="Simulated per-ticker API latency in seconds (default 1.0)")
    args = parser.parse_args()

    console.print(f"\n[bold]Benchmarking {len(args.tickers)} tickers with {args.simulate_latency}s simulated latency...[/bold]\n")
    result = benchmark(args.tickers, workers=args.workers, latency=args.simulate_latency)

    table = Table(title="Benchmark Results", show_lines=False)
    table.add_column("Metric", style="bold", width=30)
    table.add_column("Value", width=20)
    table.add_row("Tickers", str(result["tickers"]))
    table.add_row("Simulated latency", f"{result['simulated_latency_sec']}s")
    table.add_row("Parallel workers", str(result["workers"]))
    table.add_row("Sequential time", f"{result['sequential_secs']}s")
    table.add_row("Parallel time", f"{result['parallel_secs']}s")
    table.add_row("Speedup factor", f"{result['speedup_factor']}x", )

    console.print(table)


if __name__ == "__main__":
    main()
