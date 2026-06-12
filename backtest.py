"""Simple moving-average crossover backtest for historical performance analysis.

Simulates a long-only strategy that buys when the short SMA crosses above the long SMA
and sells when the short crosses below. Computes performance metrics: total return,
annualised return, Sharpe ratio, max drawdown, and number of trades.

Usage:
    python backtest.py NVDA
    python backtest.py AAPL --short 20 --long 100 --period 2y --output nvda_backtest.json
"""

import argparse
import json
import math
from pathlib import Path

import yfinance as yf
from rich.console import Console
from rich.table import Table

console = Console()

TRADING_DAYS = 252
RISK_FREE_RATE = 0.05


def run_backtest(
    ticker: str,
    short_window: int = 50,
    long_window: int = 200,
    period: str = "5y",
    initial_capital: float = 10_000.0,
) -> dict:
    """Run a dual-SMA crossover backtest for *ticker*.

    Returns a dict with performance metrics and trade log.
    """
    data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if data.empty:
        return {"error": f"No price data for {ticker}"}

    prices = data["Close"].squeeze()

    if len(prices) < long_window + 10:
        return {"error": f"Insufficient history: need >{long_window + 10} trading days"}

    short_sma = prices.rolling(short_window).mean()
    long_sma = prices.rolling(long_window).mean()

    signal = (short_sma > long_sma).astype(int)
    crossover = signal.diff()

    trades: list[dict] = []
    position = 0.0
    cash = initial_capital
    shares = 0.0

    for date, row_signal, cross in zip(prices.index, signal, crossover):
        price = float(prices.loc[date])
        if cross == 1:  # Buy signal
            if cash > 0:
                shares = cash / price
                cash = 0.0
                position = shares * price
                trades.append({"date": str(date.date()), "action": "BUY", "price": round(price, 2)})
        elif cross == -1:  # Sell signal
            if shares > 0:
                cash = shares * price
                shares = 0.0
                position = 0.0
                trades.append({"date": str(date.date()), "action": "SELL", "price": round(price, 2)})

    # Final portfolio value
    final_value = cash + shares * float(prices.iloc[-1])
    total_return = (final_value - initial_capital) / initial_capital

    # Annualised return
    years = len(prices) / TRADING_DAYS
    ann_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    # Daily returns for Sharpe
    daily_rets = prices.pct_change().dropna()
    ann_vol = float(daily_rets.std() * math.sqrt(TRADING_DAYS))
    sharpe = (ann_return - RISK_FREE_RATE) / ann_vol if ann_vol else 0.0

    # Max drawdown
    cumulative = (1 + daily_rets).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min())

    # Buy-and-hold comparison
    bh_return = (float(prices.iloc[-1]) - float(prices.iloc[0])) / float(prices.iloc[0])

    return {
        "ticker": ticker.upper(),
        "strategy": f"SMA({short_window}/{long_window}) crossover",
        "period": period,
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return * 100, 2),
        "annualised_return_pct": round(ann_return * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "num_trades": len(trades),
        "buy_and_hold_return_pct": round(bh_return * 100, 2),
        "alpha_vs_bh_pct": round((total_return - bh_return) * 100, 2),
        "trades": trades,
    }


def print_results(result: dict) -> None:
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        return

    table = Table(title=f"Backtest: {result['ticker']} — {result['strategy']}", show_lines=False)
    table.add_column("Metric", style="bold", width=30)
    table.add_column("Value", width=20)

    metrics = [
        ("Period", result["period"]),
        ("Initial Capital", f"${result['initial_capital']:,.0f}"),
        ("Final Value", f"${result['final_value']:,.2f}"),
        ("Total Return", f"{result['total_return_pct']:.2f}%"),
        ("Annualised Return", f"{result['annualised_return_pct']:.2f}%"),
        ("Sharpe Ratio", str(result["sharpe_ratio"])),
        ("Max Drawdown", f"{result['max_drawdown_pct']:.2f}%"),
        ("Number of Trades", str(result["num_trades"])),
        ("Buy-and-Hold Return", f"{result['buy_and_hold_return_pct']:.2f}%"),
        ("Alpha vs B&H", f"{result['alpha_vs_bh_pct']:+.2f}%"),
    ]
    for metric, value in metrics:
        table.add_row(metric, value)

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="SMA crossover backtester")
    parser.add_argument("ticker", help="Stock ticker, e.g. NVDA")
    parser.add_argument("--short", type=int, default=50, help="Short SMA window (default 50)")
    parser.add_argument("--long", type=int, default=200, help="Long SMA window (default 200)")
    parser.add_argument("--period", default="5y", help="History period: 1y, 2y, 5y, 10y (default 5y)")
    parser.add_argument("--capital", type=float, default=10_000.0, help="Starting capital (default 10000)")
    parser.add_argument("--output", "-o", default=None, help="Save results JSON to file")
    args = parser.parse_args()

    console.print(f"\n[bold]Running {args.short}/{args.long} SMA crossover on {args.ticker.upper()}...[/bold]\n")
    result = run_backtest(args.ticker, args.short, args.long, args.period, args.capital)
    print_results(result)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
        console.print(f"\n[green]Results saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
