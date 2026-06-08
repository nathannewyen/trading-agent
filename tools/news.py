"""Structured news aggregation combining DuckDuckGo search with sentiment scoring.

Provides a higher-level interface than raw search: fetches news for a ticker
across multiple query templates and deduplicates results by URL.
"""

import logging
from datetime import datetime

from tools.search import duckduckgo_search
from tools.sentiment import score_results

logger = logging.getLogger(__name__)

_QUERY_TEMPLATES = [
    "{ticker} stock news today",
    "{ticker} earnings analyst upgrade downgrade",
    "{ticker} product launch partnership acquisition",
]


def get_news(ticker: str, max_per_query: int = 5) -> dict:
    """Fetch and deduplicate news for *ticker* across multiple query templates.

    Returns a dict with keys:
      - articles: deduplicated list of scored news items
      - article_count: total unique articles found
      - aggregate_sentiment: float in [-1, 1]
      - sentiment_label: "positive" | "negative" | "neutral"
      - fetched_at: ISO timestamp
    """
    seen_urls: set[str] = set()
    all_articles: list[dict] = []

    for template in _QUERY_TEMPLATES:
        query = template.format(ticker=ticker.upper())
        results = duckduckgo_search(query, max_results=max_per_query)
        for item in results:
            if item.get("_type") == "sentiment_aggregate":
                continue
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(item)

    scored = score_results(all_articles)

    sentiments = [a.get("sentiment", 0.0) for a in scored if isinstance(a.get("sentiment"), float)]
    avg = sum(sentiments) / len(sentiments) if sentiments else 0.0

    if avg > 0.1:
        label = "positive"
    elif avg < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return {
        "ticker": ticker.upper(),
        "articles": scored,
        "article_count": len(scored),
        "aggregate_sentiment": round(avg, 3),
        "sentiment_label": label,
        "fetched_at": datetime.utcnow().isoformat(),
    }
