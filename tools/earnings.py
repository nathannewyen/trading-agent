import logging
import yfinance as yf
from tools import cache

logger = logging.getLogger(__name__)


def get_earnings_data(ticker: str, quarters: int = 4) -> dict:
    quarters = min(max(1, quarters), 8)
    ticker = ticker.upper()

    cached = cache.get("earnings", ticker=ticker, quarters=quarters)
    if cached is not None:
        return cached

    try:
        stock = yf.Ticker(ticker, session=None)
        info = stock.info

        result: dict = {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "analyst_rating": info.get("recommendationKey"),
            "target_price": info.get("targetMeanPrice"),
            "short_float": info.get("shortPercentOfFloat"),
            "beta": info.get("beta"),
        }

        # Quarterly income statement (try new API, fall back to legacy)
        try:
            fin = stock.get_income_stmt(freq="quarterly")
        except Exception:
            fin = stock.quarterly_financials

        if fin is not None and not fin.empty:
            cols = list(fin.columns)[:quarters]
            rows = []
            for col in cols:
                entry = {"quarter": str(col)[:10]}
                for label in ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]:
                    if label in fin.index:
                        val = fin.loc[label, col]
                        entry[label.lower().replace(" ", "_")] = (
                            int(val) if val == val and val is not None else None
                        )
                rows.append(entry)
            result["quarterly_financials"] = rows

        # EPS surprise history
        try:
            eq = stock.get_earnings_dates(limit=quarters * 2)
            if eq is not None and not eq.empty:
                recent = eq.dropna(subset=["EPS Estimate", "Reported EPS"]).head(quarters)
                result["earnings_surprises"] = [
                    {
                        "date": str(idx)[:10],
                        "estimated_eps": float(row["EPS Estimate"]),
                        "actual_eps": float(row["Reported EPS"]),
                        "surprise_pct": round(
                            (float(row["Reported EPS"]) - float(row["EPS Estimate"]))
                            / abs(float(row["EPS Estimate"])) * 100,
                            2,
                        )
                        if row["EPS Estimate"] != 0
                        else None,
                    }
                    for idx, row in recent.iterrows()
                ]
        except Exception as exc:
            logger.debug(f"Could not fetch earnings dates for {ticker}: {exc}")

        # Insider transactions (last 10)
        try:
            insider = stock.insider_transactions
            if insider is not None and not insider.empty:
                result["insider_transactions"] = insider.head(10)[
                    ["Shares", "Value", "Text", "Start Date"]
                ].to_dict("records")
        except Exception:
            pass

        # Institutional holders (top 10)
        try:
            inst = stock.institutional_holders
            if inst is not None and not inst.empty:
                result["top_institutional_holders"] = inst.head(10).to_dict("records")
        except Exception:
            pass

        cache.set("earnings", result, ticker=ticker, quarters=quarters)
        return result

    except Exception as exc:
        logger.error(f"Error fetching data for {ticker}: {exc}")
        return {"error": f"Failed to fetch data for {ticker}: {exc}", "ticker": ticker}
