"""Watchlist mode — check upcoming earnings and auto-research tickers within N days.

Combines the earnings calendar with the research agent: finds which tickers
in your watchlist have earnings coming up soon, then runs the full thesis pipeline
on those so you're prepared ahead of the catalyst.

Usage:
  python watchlist.py NVDA AAPL MSFT TSLA META AMZN --days 14
  python watchlist.py --watchlist-file tickers.txt --days 30 --output pre_earnings_report.md
"""

import argparse
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from agent import run_agent
from prompts.earnings_preview import EARNINGS_PREVIEW_PROMPT
from tools.calendar import get_earnings_calendar, get_earnings_surprise_history

console = Console()


def _days_color(days_until: int) -> str:
    """Return a Rich color name based on how close the earnings date is."""
    if days_until <= 7:
        return "red"
    if days_until <= 14:
        return "yellow"
    return "green"


def _load_tickers_from_file(path: str) -> list[str]:
    """Read one ticker per line from a text file, stripping blanks and comments."""
    lines = Path(path).read_text().splitlines()
    tickers = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            tickers.append(line.upper())
    return tickers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research tickers with upcoming earnings within N days"
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Watchlist ticker symbols (can be omitted if --watchlist-file is given)",
    )
    parser.add_argument(
        "--watchlist-file",
        metavar="FILE",
        default=None,
        help="Path to a text file with one ticker per line",
    )
    parser.add_argument(
        "--days", type=int, default=14, help="Lookahead window in days (default 14)"
    )
    parser.add_argument("--output", "-o", default=None, help="Save full report to file")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously refresh every --interval minutes until interrupted",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="MIN",
        help="Refresh interval in minutes when --watch is active (default 60)",
    )
    parser.add_argument(
        "--webhook",
        default=None,
        metavar="URL",
        help="POST a JSON summary to this URL after each research run completes",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="TICKER",
        default=[],
        help="Skip these tickers even if they appear in the watchlist",
    )
    args = parser.parse_args()

    # Resolve ticker list
    tickers = list(args.tickers)
    if args.watchlist_file:
        tickers += _load_tickers_from_file(args.watchlist_file)

    if args.exclude:
        excluded = {t.upper() for t in args.exclude}
        tickers = [t for t in tickers if t.upper() not in excluded]
    if not tickers:
        parser.error("Provide at least one ticker or --watchlist-file.")

    console.print(
        f"\n[bold]Checking earnings calendar for {len(tickers)} ticker(s) — "
        f"{args.days}d lookahead[/bold]\n"
    )

    upcoming = get_earnings_calendar(tickers, days_ahead=args.days)

    if not upcoming:
        console.print(
            f"[yellow]No earnings found in the next {args.days} days for this watchlist.[/yellow]"
        )
        console.print("Tip: broaden with --days 30 or add more tickers.")
        return

    # Print calendar summary
    cal_table = Table(title=f"Upcoming Earnings (next {args.days} days)")
    cal_table.add_column("Ticker", style="cyan bold")
    cal_table.add_column("Date")
    cal_table.add_column("Days Away")
    cal_table.add_column("EPS Est.")
    cal_table.add_column("Last Surprise")

    for row in upcoming:
        days = row["days_until"]
        color = _days_color(days)
        surprise = get_earnings_surprise_history(row["ticker"])
        surprise_str = "—"
        if surprise:
            last = surprise[0]
            direction = "beat" if last.get("surprise_pct", 0) > 0 else "miss"
            pct = abs(last.get("surprise_pct", 0))
            surprise_str = f"{direction} {pct:.1f}%"

        cal_table.add_row(
            row["ticker"],
            f"[{color}]{row['earnings_date']}[/{color}]",
            f"[{color}]{days}[/{color}]",
            f"${row['estimated_eps']:.2f}" if row.get("estimated_eps") is not None else "—",
            surprise_str,
        )

    console.print(cal_table)
    console.print()

    # Research each upcoming ticker
    reports = []
    for row in upcoming:
        ticker = row["ticker"]
        console.print(f"[bold]Researching {ticker}[/bold] (earnings in {row['days_until']} days)...")
        question = EARNINGS_PREVIEW_PROMPT.format(
            ticker=ticker,
            days_until=row["days_until"],
        )
        thesis = run_agent(ticker, question=question)
        reports.append({"ticker": ticker, "days_until": row["days_until"], "thesis": thesis})
        console.print(f"[green]Done — {ticker}[/green]\n")

    if args.output:
        lines = ["# Pre-Earnings Research Report\n\n"]
        for r in reports:
            lines.append(
                f"## {r['ticker']} (earnings in {r['days_until']} days)\n\n{r['thesis']}\n\n---\n\n"
            )
        Path(args.output).write_text("".join(lines))
        console.print(f"[green]Report saved to {args.output}[/green]")

    if args.webhook and reports:
        import json as _json
        import urllib.request as _req
        summary = [{"ticker": r["ticker"], "days_until": r["days_until"]} for r in reports]
        payload = _json.dumps({"watchlist_run": summary}).encode("utf-8")
        try:
            req = _req.Request(
                args.webhook, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with _req.urlopen(req, timeout=5) as resp:
                console.print(f"[dim]Webhook delivered: HTTP {resp.status}[/dim]")
        except Exception as exc:
            console.print(f"[yellow]Webhook delivery failed: {exc}[/yellow]")

    if args.watch:
        console.print(f"\n[dim]--watch active: refreshing every {args.interval} min. Ctrl-C to stop.[/dim]")
        try:
            while True:
                time.sleep(args.interval * 60)
                console.print(f"\n[bold cyan]Refreshing watchlist...[/bold cyan]")
                upcoming = get_earnings_calendar(tickers, days_ahead=args.days)
                if upcoming:
                    for row in upcoming:
                        days = row["days_until"]
                        color = _days_color(days)
                        console.print(
                            f"  [{color}]{row['ticker']}[/{color}] — earnings in {days} days"
                        )
                else:
                    console.print("[yellow]No upcoming earnings in window.[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[dim]Watch mode stopped.[/dim]")


if __name__ == "__main__":
    main()
