"""Unit tests for tools/news.py."""

from unittest.mock import patch

from tools.news import get_news

_MOCK_SEARCH = [
    {"title": "NVDA beats earnings", "url": "http://example.com/1", "snippet": "...", "sentiment": 0.8},
    {"title": "NVDA faces headwinds", "url": "http://example.com/2", "snippet": "...", "sentiment": -0.3},
    {"_type": "sentiment_aggregate", "score": 0.25, "label": "positive", "count": 2},
]


@patch("tools.news.duckduckgo_search", return_value=_MOCK_SEARCH)
@patch("tools.news.score_results", side_effect=lambda x: x)
def test_returns_expected_structure(mock_score, mock_search):
    result = get_news("NVDA")
    assert "articles" in result
    assert "aggregate_sentiment" in result
    assert "sentiment_label" in result
    assert result["ticker"] == "NVDA"


@patch("tools.news.duckduckgo_search", return_value=_MOCK_SEARCH)
@patch("tools.news.score_results", side_effect=lambda x: x)
def test_filters_sentiment_aggregate_elements(mock_score, mock_search):
    result = get_news("NVDA")
    for article in result["articles"]:
        assert article.get("_type") != "sentiment_aggregate"


@patch("tools.news.duckduckgo_search", return_value=[])
@patch("tools.news.score_results", side_effect=lambda x: x)
def test_empty_results_return_neutral(mock_score, mock_search):
    result = get_news("UNKNOWN")
    assert result["aggregate_sentiment"] == 0.0
    assert result["sentiment_label"] == "neutral"
    assert result["article_count"] == 0


@patch("tools.news.duckduckgo_search", return_value=_MOCK_SEARCH)
@patch("tools.news.score_results", side_effect=lambda x: x)
def test_deduplicates_by_url(mock_score, mock_search):
    # Same URL returned three times across three query templates
    result = get_news("NVDA")
    urls = [a["url"] for a in result["articles"]]
    assert len(urls) == len(set(urls))


@patch("tools.news.duckduckgo_search", return_value=_MOCK_SEARCH)
@patch("tools.news.score_results", side_effect=lambda x: x)
def test_ticker_uppercased(mock_score, mock_search):
    result = get_news("nvda")
    assert result["ticker"] == "NVDA"
