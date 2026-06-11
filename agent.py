"""Trading Research Agent — Anthropic tool-use loop with retry + context management."""

__version__ = "0.6.0"

import argparse
import json
import logging
import time

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import (
    CONTEXT_TOKEN_LIMIT,
    MAX_ITERATIONS,
    MAX_OUTPUT_TOKENS,
    MAX_RETRIES,
    MODEL,
)
from prompts.system import SYSTEM_PROMPT
from tools.calculator import calculate
from tools.earnings import get_earnings_data
from tools.macro import get_macro
from tools.options import get_options_data
from tools.risk import get_risk_metrics
from tools.search import duckduckgo_search
from tools.technicals import get_technicals

load_dotenv()

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
console = Console()

TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for recent news about a stock or company. "
            "Use for earnings results, analyst upgrades/downgrades, product launches, sector trends."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'NVDA Q1 2025 earnings results'",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_earnings",
        "description": (
            "Fetch earnings history, revenue, EPS, margins, valuation multiples, "
            "analyst targets, insider transactions, and institutional holders via Yahoo Finance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. 'NVDA'"},
                "quarters": {
                    "type": "integer",
                    "description": "Number of recent quarters to include (1-8). Default 4.",
                    "default": 4,
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_technicals",
        "description": (
            "Compute technical indicators from price history: RSI(14), MACD(12,26,9), "
            "SMA(50/200), EMA(20), golden/death cross, 52-week range, volume ratio."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. 'NVDA'"},
                "period": {
                    "type": "string",
                    "description": "History period: '3mo', '6mo', '1y', '2y'. Default '1y'.",
                    "default": "1y",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_options",
        "description": (
            "Fetch options market data: put/call ratio, ATM implied volatility, "
            "open interest. Useful for gauging market sentiment and hedging activity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. 'NVDA'"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "calculate",
        "description": (
            "Evaluate a mathematical expression for financial calculations: "
            "growth rates, P/E ratios, margin changes, risk/reward ratios, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression, e.g. '(125.4 - 98.2) / 98.2 * 100'",
                },
                "description": {
                    "type": "string",
                    "description": "What this calculates, e.g. 'Revenue YoY growth %'",
                },
            },
            "required": ["expression", "description"],
        },
    },
    {
        "name": "get_macro",
        "description": (
            "Fetch macro market context: VIX (fear gauge), 10-year Treasury yield, "
            "and SPY trend (SMA50/200). Call this first to understand the market regime "
            "before forming a single-stock thesis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_risk",
        "description": (
            "Compute risk metrics for a stock: beta vs SPY, annualised volatility, "
            "Sharpe ratio, max drawdown, and correlation to the S&P 500."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. 'NVDA'"},
                "period": {
                    "type": "string",
                    "description": "History period: '3mo', '6mo', '1y', '2y'. Default '1y'.",
                    "default": "1y",
                },
            },
            "required": ["ticker"],
        },
    },
]


def _dispatch_tool(name: str, tool_input: dict) -> object:
    if name == "web_search":
        return duckduckgo_search(
            query=tool_input["query"],
            max_results=tool_input.get("max_results", 5),
        )
    if name == "get_earnings":
        return get_earnings_data(
            ticker=tool_input["ticker"],
            quarters=tool_input.get("quarters", 4),
        )
    if name == "get_technicals":
        return get_technicals(
            ticker=tool_input["ticker"],
            period=tool_input.get("period", "1y"),
        )
    if name == "get_options":
        return get_options_data(ticker=tool_input["ticker"])
    if name == "calculate":
        return calculate(
            expression=tool_input["expression"],
            description=tool_input.get("description", ""),
        )
    if name == "get_macro":
        return get_macro()
    if name == "get_risk":
        return get_risk_metrics(
            ticker=tool_input["ticker"],
            period=tool_input.get("period", "1y"),
        )
    return {"error": f"Unknown tool: {name}"}


def _estimate_tokens(messages: list[dict]) -> int:
    return sum(len(json.dumps(m)) for m in messages) // 4


def _truncate_messages(messages: list[dict]) -> list[dict]:
    """Drop oldest assistant+tool_result pairs to stay under the context limit.

    Removes from index 1 in steps of 2 (assistant turn, then the following
    user/tool_result turn) so we never leave an orphaned tool_result block
    without its preceding tool_use — the API returns 400 on that.
    Always preserves messages[0] (the original research request).
    """
    while len(messages) > 3 and _estimate_tokens(messages) > CONTEXT_TOKEN_LIMIT:
        # Drop the oldest assistant message and its paired tool_result user message
        messages.pop(1)  # assistant (tool_use blocks)
        if len(messages) > 1:
            messages.pop(1)  # user (tool_result blocks)
    return messages


def _call_api(messages: list[dict], system: str | None = None) -> anthropic.types.Message:
    for attempt in range(MAX_RETRIES):
        try:
            return client.messages.create(
                model=MODEL,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system or SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
        except anthropic.RateLimitError:
            wait = 5 * (2**attempt)
            logger.warning(f"Rate limit — retrying in {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
        except anthropic.APIStatusError as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2**attempt
            logger.warning(f"API error {exc.status_code} — retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Max retries exceeded")


def stream_agent(ticker: str, question: str | None = None, sector: str | None = None) -> None:
    """Stream the final thesis text to stdout as it arrives from the API.

    Unlike run_agent (which buffers the full response), this function prints
    each text delta immediately using the Anthropic streaming API.  Tool-use
    turns are handled silently; only the final synthesis is streamed.
    """
    from prompts.sector import get_sector_prompt
    system = (get_sector_prompt(sector) if sector else None) or SYSTEM_PROMPT

    if question is None:
        question = (
            f"Research {ticker.upper()} and produce a complete trade thesis. "
            "Fetch earnings data, technical indicators, options sentiment, and recent news. "
            "Calculate key growth metrics. Write the full structured thesis."
        )

    messages: list[dict] = [{"role": "user", "content": question}]

    for _ in range(MAX_ITERATIONS):
        if _estimate_tokens(messages) > CONTEXT_TOKEN_LIMIT:
            messages = _truncate_messages(messages)

        # Non-streaming pass for tool calls; stream only the final text turn
        response = _call_api(messages, system=system)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Re-call with streaming enabled for the text output
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=messages[:-1],  # exclude the buffered assistant turn
            ) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
            print()
            return

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _dispatch_tool(block.name, block.input)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                    )
            messages.append({"role": "user", "content": tool_results})
        else:
            break


def run_agent(ticker: str, question: str | None = None, sector: str | None = None) -> str:
    """Run the research agent and return a completed trade thesis string."""
    from prompts.sector import get_sector_prompt
    system = (get_sector_prompt(sector) if sector else None) or SYSTEM_PROMPT

    if question is None:
        question = (
            f"Research {ticker.upper()} and produce a complete trade thesis. "
            "Fetch earnings data, technical indicators, options sentiment, and recent news. "
            "Calculate key growth metrics. Write the full structured thesis."
        )

    messages: list[dict] = [{"role": "user", "content": question}]
    tool_call_counts: dict[str, int] = {}

    for iteration in range(1, MAX_ITERATIONS + 1):
        if _estimate_tokens(messages) > CONTEXT_TOKEN_LIMIT:
            messages = _truncate_messages(messages)

        response = _call_api(messages, system=system)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    if tool_call_counts:
                        logger.info(f"Tool calls: {tool_call_counts}")
                    return block.text
            return "No thesis generated."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Tool: {block.name}({json.dumps(block.input)[:100]})")
                    tool_call_counts[block.name] = tool_call_counts.get(block.name, 0) + 1
                    result = _dispatch_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    logger.warning(f"Agent hit max iterations ({MAX_ITERATIONS})")
    return "Research incomplete: max iterations reached."


def main() -> None:
    parser = argparse.ArgumentParser(description="Trading Research Agent")
    parser.add_argument("ticker", help="Stock ticker, e.g. NVDA")
    parser.add_argument("--question", "-q", default=None, help="Custom research question")
    parser.add_argument("--output", "-o", default=None, help="Save thesis to file")
    parser.add_argument("--critique", action="store_true", help="Run two-agent critic after research")
    parser.add_argument("--no-cache", action="store_true", help="Bypass disk cache for fresh data")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of rendered markdown")
    parser.add_argument("--version", action="version", version=f"trading-agent {__version__}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log every tool call to stderr")
    parser.add_argument("--sector", default=None, help="Sector lens: tech, energy, financials, healthcare, consumer")
    parser.add_argument("--stream", action="store_true", help="Stream final thesis text to stdout as it is generated")
    parser.add_argument("--show-risk", action="store_true", help="Print risk metrics table before thesis output")
    parser.add_argument("--alert-above", type=float, default=None, metavar="PRICE",
                        help="Fire an alert if the current price is at or above PRICE")
    parser.add_argument("--alert-below", type=float, default=None, metavar="PRICE",
                        help="Fire an alert if the current price is at or below PRICE")
    parser.add_argument("--webhook", default=None, metavar="URL",
                        help="POST alert payloads to this webhook URL")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    # Input validation
    ticker_raw = args.ticker.strip()
    if not ticker_raw:
        parser.error("Ticker cannot be empty.")
    if ticker_raw.isdigit():
        parser.error(f"Invalid ticker '{ticker_raw}': must contain letters, not digits only.")
    if len(ticker_raw) > 6:
        parser.error(f"Invalid ticker '{ticker_raw}': tickers are at most 6 characters.")
    args.ticker = ticker_raw.upper()

    if args.no_cache:
        from tools import cache as _cache
        cleared = _cache.clear_all()
        logger.info(f"Cache cleared ({cleared} entries)")

    if args.alert_above is not None or args.alert_below is not None:
        from tools.alerts import check_price_alert
        if args.alert_above is not None:
            alert = check_price_alert(args.ticker, args.alert_above, "above", webhook_url=args.webhook)
            color = "green" if alert.get("triggered") else "dim"
            console.print(f"[{color}]{alert['message']}[/{color}]")
        if args.alert_below is not None:
            alert = check_price_alert(args.ticker, args.alert_below, "below", webhook_url=args.webhook)
            color = "red" if alert.get("triggered") else "dim"
            console.print(f"[{color}]{alert['message']}[/{color}]")

    if args.stream:
        console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        console.print(f"[bold cyan]TRADE THESIS: {args.ticker.upper()} (streaming)[/bold cyan]")
        console.print(f"[bold blue]{'='*60}[/bold blue]\n")
        stream_agent(args.ticker, args.question, sector=args.sector)
        return

    if args.show_risk:
        from tools.risk import get_risk_metrics
        from rich.table import Table as RichTable
        risk = get_risk_metrics(args.ticker)
        rt = RichTable(title=f"Risk Metrics: {args.ticker}", show_lines=False)
        for k, v in risk.items():
            if k not in ("ticker", "period", "data_points"):
                rt.add_row(k.replace("_", " ").title(), str(v))
        console.print(rt)
        console.print()

    with Progress(SpinnerColumn(), TextColumn(f"Researching {args.ticker.upper()}..."), console=console) as p:
        p.add_task("", total=None)
        thesis = run_agent(args.ticker, args.question, sector=args.sector)

    if args.json:
        import datetime
        payload = json.dumps(
            {"ticker": args.ticker.upper(), "date": str(datetime.date.today()), "thesis": thesis},
            indent=2,
        )
        print(payload)
        if args.output:
            with open(args.output, "w") as fh:
                fh.write(payload)
        return

    console.print(f"\n[bold blue]{'='*60}[/bold blue]")
    console.print(f"[bold cyan]TRADE THESIS: {args.ticker.upper()}[/bold cyan]")
    console.print(f"[bold blue]{'='*60}[/bold blue]\n")
    console.print(Markdown(thesis))

    if args.critique:
        from critic import run_full_analysis
        with Progress(SpinnerColumn(), TextColumn("Running critic agent..."), console=console) as p:
            p.add_task("", total=None)
            result = run_full_analysis(args.ticker, thesis)

        console.print(f"\n[bold yellow]{'='*60}[/bold yellow]")
        console.print("[bold yellow]ANALYST CRITIQUE[/bold yellow]")
        console.print(f"[bold yellow]{'='*60}[/bold yellow]\n")
        console.print(Markdown(result["critique"]))

        if args.output:
            with open(args.output, "w") as fh:
                fh.write(result["combined"])
            console.print(f"\n[green]Full analysis saved to {args.output}[/green]")
    elif args.output:
        with open(args.output, "w") as fh:
            fh.write(thesis)
        console.print(f"\n[green]Thesis saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
