"""Async parallel portfolio research using asyncio + ThreadPoolExecutor.

Runs multiple tickers concurrently to reduce total wall-clock time for large
watchlists.  The underlying agent calls are synchronous (Anthropic SDK), so
we use a thread pool rather than native coroutines.

Usage:
    python async_portfolio.py NVDA AAPL MSFT TSLA --workers 4
    python async_portfolio.py NVDA AMD INTC --output parallel_report.md
"""

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agent import run_agent
from config import PARALLEL_WORKERS
from portfolio import (
    _extract_bias,
    _extract_confidence,
    _extract_sector,
    _score_thesis,
    export_csv,
    print_summary,
)

console = Console()


def _research_one(ticker: str) -> dict:
    thesis = run_agent(ticker)
    return {
        "ticker": ticker.upper(),
        "thesis": thesis,
        "score": _score_thesis(thesis),
        "bias": _extract_bias(thesis),
        "confidence": _extract_confidence(thesis),
        "sector": _extract_sector(thesis),
    }


def run_parallel_portfolio(tickers: list[str], workers: int = PARALLEL_WORKERS) -> list[dict]:
    """Research *tickers* concurrently using a thread pool."""
    results: list[dict] = []
    total = len(tickers)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        tasks = {t: progress.add_task(f"Queued: {t}", total=None) for t in tickers}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_ticker = {executor.submit(_research_one, t): t for t in tickers}
            done_count = 0

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                done_count += 1
                progress.update(tasks[ticker], description=f"[{done_count}/{total}] Done: {ticker}")
                try:
                    results.append(future.result())
                except Exception as exc:
                    console.print(f"[red]Error researching {ticker}: {exc}[/red]")
                    results.append({"ticker": ticker, "error": str(exc), "score": 0.0,
                                    "bias": "—", "confidence": "—", "sector": "—"})

    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel portfolio research using thread pool")
    parser.add_argument("tickers", nargs="+", help="Ticker symbols")
    parser.add_argument("--workers", type=int, default=PARALLEL_WORKERS,
                        help=f"Max concurrent workers (default {PARALLEL_WORKERS})")
    parser.add_argument("--output", "-o", default=None, help="Save full report to file")
    parser.add_argument("--csv", default=None, metavar="FILE", help="Export ranked results to CSV")
    args = parser.parse_args()

    console.print(f"\n[bold]Researching {len(args.tickers)} ticker(s) with {args.workers} parallel workers...[/bold]\n")
    results = run_parallel_portfolio(args.tickers, workers=args.workers)
    print_summary(results)

    if args.csv:
        export_csv(results, args.csv)

    if args.output:
        report = "\n\n---\n\n".join(
            f"# {r['ticker']} (Score: {r.get('score', 0)})\n\n{r.get('thesis', r.get('error', ''))}"
            for r in results
        )
        Path(args.output).write_text(report)
        console.print(f"\n[green]Full report saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
