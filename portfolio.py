"""Portfolio analysis mode — run the research agent on multiple tickers and rank by thesis score.

Usage:
  python portfolio.py NVDA AAPL MSFT TSLA
  python portfolio.py NVDA AAPL --output portfolio_report.md
"""

import argparse
import re
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agent import run_agent

console = Console()

REQUIRED_SECTIONS = [
    "Company Snapshot",
    "Earnings Analysis",
    "Bull Case",
    "Bear Case",
    "Trade Recommendation",
]
NUMBER_PATTERNS = [
    r"\$[\d,.]+",
    r"[\d.]+%",
    r"[\d.]+x\b",
]
BIAS_RE = re.compile(r"\*\*Bias:\*\*\s*(Bullish|Bearish|Neutral)", re.IGNORECASE)
CONFIDENCE_RE = re.compile(r"\*\*Confidence:\*\*\s*(High|Medium|Low)", re.IGNORECASE)


def _score_thesis(thesis: str) -> float:
    section_score = sum(1 for s in REQUIRED_SECTIONS if s in thesis) / len(REQUIRED_SECTIONS)
    data_points = sum(len(re.findall(p, thesis)) for p in NUMBER_PATTERNS)
    data_score = min(1.0, data_points / 15)
    has_rec = 1.0 if BIAS_RE.search(thesis) else 0.0
    return round((section_score * 0.4 + data_score * 0.4 + has_rec * 0.2), 3)


def _extract_bias(thesis: str) -> str:
    m = BIAS_RE.search(thesis)
    return m.group(1) if m else "—"


def _extract_confidence(thesis: str) -> str:
    m = CONFIDENCE_RE.search(thesis)
    return m.group(1) if m else "—"


def _extract_sector(thesis: str) -> str:
    m = re.search(r"\*\*Sector:\*\*\s*([^|]+)", thesis)
    return m.group(1).strip() if m else "—"


def run_portfolio(tickers: list[str]) -> list[dict]:
    results = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        for ticker in tickers:
            task = progress.add_task(f"Researching {ticker}...", total=None)
            thesis = run_agent(ticker)
            progress.remove_task(task)
            results.append(
                {
                    "ticker": ticker.upper(),
                    "thesis": thesis,
                    "score": _score_thesis(thesis),
                    "bias": _extract_bias(thesis),
                    "confidence": _extract_confidence(thesis),
                    "sector": _extract_sector(thesis),
                }
            )

    return sorted(results, key=lambda x: x["score"], reverse=True)


def print_summary(results: list[dict]) -> None:
    table = Table(title="Portfolio Analysis", show_lines=True)
    table.add_column("Rank", style="bold", width=6)
    table.add_column("Ticker", style="cyan bold", width=8)
    table.add_column("Sector", width=22)
    table.add_column("Bias", width=10)
    table.add_column("Confidence", width=12)
    table.add_column("Quality Score", width=14)

    bias_colors = {"Bullish": "green", "Bearish": "red", "Neutral": "yellow"}

    for i, r in enumerate(results, 1):
        bias = r["bias"]
        color = bias_colors.get(bias, "white")
        table.add_row(
            str(i),
            r["ticker"],
            r.get("sector", "—"),
            f"[{color}]{bias}[/{color}]",
            r["confidence"],
            f"{r['score']:.3f}",
        )

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio research — rank multiple tickers")
    parser.add_argument("tickers", nargs="+", help="Ticker symbols, e.g. NVDA AAPL MSFT")
    parser.add_argument("--output", "-o", default=None, help="Save full report to file")
    args = parser.parse_args()

    console.print(f"\n[bold]Researching {len(args.tickers)} ticker(s)...[/bold]\n")
    results = run_portfolio(args.tickers)
    print_summary(results)

    if args.output:
        report = "\n\n---\n\n".join(
            f"# {r['ticker']} (Score: {r['score']})\n\n{r['thesis']}" for r in results
        )
        Path(args.output).write_text(report)
        console.print(f"\n[green]Full report saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
