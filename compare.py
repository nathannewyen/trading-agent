"""Side-by-side stock comparison — research two tickers and ask Claude to compare them.

Usage:
  python compare.py NVDA AMD
  python compare.py AAPL MSFT --output comparison.md
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

load_dotenv()

client = anthropic.Anthropic()
MODEL = "claude-opus-4-7"
console = Console()
logger = logging.getLogger(__name__)

COMPARE_SYSTEM = """You are a trading analyst comparing two stocks side-by-side.

Given two completed trade theses, produce:

## Comparison: [TICKER_A] vs [TICKER_B]

### Head-to-Head Metrics
| Metric | [TICKER_A] | [TICKER_B] | Edge |
|--------|-----------|-----------|------|
| Valuation (P/E) | | | |
| Revenue Growth | | | |
| Profit Margin | | | |
| Analyst Bias | | | |
| Technical Setup | | | |

### Relative Strengths
**[TICKER_A] wins on:** [2-3 specific advantages]
**[TICKER_B] wins on:** [2-3 specific advantages]

### Verdict
[Which is the stronger trade right now and why — 3-5 sentences grounded in the data above]

**Preferred Trade:** [TICKER_A / TICKER_B]
**Runner-up:** [other ticker — conditions under which it would win]
"""


def compare_stocks(ticker_a: str, ticker_b: str) -> dict:
    """Research both tickers, then run a comparison agent."""
    results = {}

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
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
    args = parser.parse_args()

    result = compare_stocks(args.ticker_a, args.ticker_b)

    console.print(f"\n[bold cyan]Comparison: {result['ticker_a']} vs {result['ticker_b']}[/bold cyan]\n")
    console.print(Markdown(result["comparison"]))

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
