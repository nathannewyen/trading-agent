"""Side-by-side stock comparison — research two tickers and ask Claude to compare them.

Usage:
  python compare.py NVDA AMD
  python compare.py AAPL MSFT --output comparison.md
  python compare.py NVDA AMD --quick     # skip full thesis, compare on earnings data only
"""

import argparse
import logging
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent import run_agent
from config import MODEL
from prompts.compare import COMPARE_SYSTEM
from tools.earnings import get_earnings_data

load_dotenv()

client = anthropic.Anthropic()
console = Console()
logger = logging.getLogger(__name__)


def compare_stocks(ticker_a: str, ticker_b: str, quick: bool = False) -> dict:
    """Research both tickers, then run a comparison agent.

    If `quick` is True, skip the full research pipeline and feed only the
    earnings data snapshot directly to the comparison agent — much faster
    for a ballpark side-by-side view.
    """
    results = {}

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        if quick:
            for ticker in [ticker_a, ticker_b]:
                task = progress.add_task(f"Fetching earnings for {ticker}...", total=None)
                import json
                data = get_earnings_data(ticker)
                results[ticker] = f"[Quick mode — earnings snapshot only]\n{json.dumps(data, indent=2)}"
                progress.remove_task(task)
        else:
            for ticker in [ticker_a, ticker_b]:
                task = progress.add_task(f"Researching {ticker}...", total=None)
                results[ticker] = run_agent(ticker)
                progress.remove_task(task)

        task = progress.add_task("Comparing...", total=None)
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=COMPARE_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Compare these two stocks:\n\n"
                        f"--- {ticker_a.upper()} THESIS ---\n{results[ticker_a]}\n\n"
                        f"--- {ticker_b.upper()} THESIS ---\n{results[ticker_b]}"
                    ),
                }
            ],
        )
        progress.remove_task(task)

    comparison = response.content[0].text
    return {
        "ticker_a": ticker_a.upper(),
        "ticker_b": ticker_b.upper(),
        "thesis_a": results[ticker_a],
        "thesis_b": results[ticker_b],
        "comparison": comparison,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Side-by-side stock comparison")
    parser.add_argument("ticker_a", help="First ticker, e.g. NVDA")
    parser.add_argument("ticker_b", help="Second ticker, e.g. AMD")
    parser.add_argument("--output", "-o", default=None, help="Save report to file")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip full thesis; compare using earnings snapshots only (faster)",
    )
    parser.add_argument(
        "--save-theses",
        action="store_true",
        help="Save each individual thesis to <TICKER>_thesis.md alongside the comparison output",
    )
    args = parser.parse_args()

    result = compare_stocks(args.ticker_a, args.ticker_b, quick=args.quick)

    console.print(f"\n[bold cyan]Comparison: {result['ticker_a']} vs {result['ticker_b']}[/bold cyan]\n")
    console.print(Markdown(result["comparison"]))

    if args.save_theses:
        Path(f"{result['ticker_a'].lower()}_thesis.md").write_text(result["thesis_a"])
        Path(f"{result['ticker_b'].lower()}_thesis.md").write_text(result["thesis_b"])
        console.print(f"[dim]Theses saved to {result['ticker_a'].lower()}_thesis.md and {result['ticker_b'].lower()}_thesis.md[/dim]")

    if args.output:
        full = (
            f"# {result['ticker_a']} vs {result['ticker_b']}\n\n"
            f"{result['comparison']}\n\n---\n\n"
            f"## {result['ticker_a']} Full Thesis\n\n{result['thesis_a']}\n\n"
            f"## {result['ticker_b']} Full Thesis\n\n{result['thesis_b']}"
        )
        Path(args.output).write_text(full)
        console.print(f"\n[green]Saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
