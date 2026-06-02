import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.sentiment import score_headline, score_results, aggregate_sentiment


def test_bullish_headline():
    score = score_headline("Apple beats earnings estimates with record revenue")
    assert score > 0


def test_bearish_headline():
    score = score_headline("Tesla misses revenue forecast, shares decline sharply")
    assert score < 0


def test_neutral_headline():
    score = score_headline("Company announces quarterly results scheduled for next week")
    assert -0.15 < score < 0.15


def test_negation_flips_sentiment():
    positive = score_headline("NVDA beats estimates")
    negated = score_headline("NVDA did not beat estimates")
    assert positive > negated


def test_score_results_adds_fields():
    results = [{"title": "Stock surges on strong earnings", "snippet": "Record revenue beat"}]
    scored = score_results(results)
    assert "sentiment" in scored[0]
    assert "sentiment_label" in scored[0]
    assert scored[0]["sentiment_label"] in ("bullish", "bearish", "neutral")


def test_aggregate_sentiment_empty():
    out = aggregate_sentiment([])
    assert out["score"] == 0.0
    assert out["n"] == 0


def test_aggregate_sentiment_counts():
    results = [
        {"sentiment": 0.5},
        {"sentiment": 0.3},
        {"sentiment": -0.4},
    ]
    out = aggregate_sentiment(results)
    assert out["bullish_count"] == 2
    assert out["bearish_count"] == 1
