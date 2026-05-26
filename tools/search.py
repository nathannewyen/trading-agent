import logging
import time

from ddgs import DDGS
from tools import cache

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
            output = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ]
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
