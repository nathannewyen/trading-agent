import logging
import time

from ddgs import DDGS
from tools import cache
from tools.sentiment import aggregate_sentiment, score_headline, score_results

logger = logging.getLogger(__name__)


def duckduckgo_search(query: str, max_results: int = 5) -> list[dict]:
    max_results = min(max(1, max_results), 10)

    cached = cache.get("search", ttl=1800, query=query, max_results=max_results)
    if cached is not None:
        return cached

    for attempt in range(3):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            raw = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ]
            # Score each result individually for per-headline sentiment
            scored = score_results(raw)

            # Append an aggregate summary as the final element so the agent
            # can quickly read overall news tone without iterating all results.
            summary = aggregate_sentiment(scored)
            output = scored + [{"_type": "sentiment_aggregate", **summary}]

            cache.set("search", output, query=query, max_results=max_results)
            return output
        except Exception as exc:
            if attempt == 2:
                logger.error(f"DuckDuckGo search failed after 3 attempts: {exc}")
                return [{"error": f"Search failed: {exc}"}]
            wait = 2**attempt
            logger.warning(f"Search attempt {attempt + 1} failed, retrying in {wait}s")
            time.sleep(wait)

    return []
