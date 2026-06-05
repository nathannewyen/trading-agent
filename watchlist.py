"""Watchlist mode — check upcoming earnings and auto-research tickers within N days.

Combines the earnings calendar with the research agent: finds which tickers
in your watchlist have earnings coming up soon, then runs the full thesis pipeline
on those so you're prepared ahead of the catalyst.

Usage:
  python watchlist.py NVDA AAPL MSFT TSLA META AMZN --days 14
  python watchlist.py NVDA AAPL MSFT --days 30 --output pre_earnings_report.md
"""

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agent import run_agent
from tools.calendar import get_earnings_calendar

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research tickers with upcoming earnings within N days"
    )
    parser.add_argument("tickers", nargs="+", help="Watchlist ticker symbols")
    parser.add_argument(
        "--days", type=int, default=14, help="Lookahead window in days (default 14)"
    )
    parser.add_argument("--output", "-o", default=None, help="Save full report to file")
    args = parser.parse_args()

    console.print(f"\n[bold]Checking earnings calendar for {len(args.tickers)} ticker(s) — {args.days}d lookahead[/bold]\n")

    upcoming = get_earnings_calendar(args.tickers, days_ahead=args.days)

    if not upcoming:
        console.print(f"[yellow]No earnings found in the next {args.days} days for this watchlist.[/yellow]")
        console.print("Tip: broaden with --days 30 or add more tickers.")
        return

    # Print calendar summary
    cal_table = Table(title=f"Upcoming Earnings (next {args.days} days)")
    cal_table.add_column("Ticker", style="cyan bold")
    cal_table.add_column("Date")
    cal_table.add_column("Days Away")
    cal_table.add_column("EPS Est.")

    for row in upcoming:
        cal_table.add_row(
            row["ticker"],
            row["earnings_date"],
            str(row["days_until"]),
            f"${row['estimated_eps']:.2f}" if row.get("estimated_eps") is not None else "—",
        )

    console.print(cal_table)
    console.print()

    # Research each upcoming ticker
    reports = []
    for row in upcoming:
        ticker = row["ticker"]
        console.print(f"[bold]Researching {ticker}[/bold] (earnings in {row['days_until']} days)...")
        thesis = run_agent(
            ticker,
            question=(
                f"Research {ticker} ahead of its earnings in {row['days_until']} days. "
                "Focus on: what consensus expects, what could surprise, key metrics to watch, "
                "and whether the risk/reward favors holding through earnings."
            ),
        )
        reports.append({"ticker": ticker, "days_until": row["days_until"], "thesis": thesis})
        console.print(f"[green]Done — {ticker}[/green]\n")

    if args.output:
        lines = [f"# Pre-Earnings Research Report\n\n"]
        for r in reports:
            lines.append(f"## {r['ticker']} (earnings in {r['days_until']} days)\n\n{r['thesis']}\n\n---\n\n")
        Path(args.output).write_text("".join(lines))
        console.print(f"[green]Report saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
