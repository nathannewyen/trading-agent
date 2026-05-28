"""Lightweight keyword-based sentiment scorer for news headlines and snippets.

No external NLP library required — uses curated financial word lists.
Returns a score in [-1.0, +1.0]: positive = bullish news, negative = bearish.
"""

BULLISH_WORDS = {
    "beat", "beats", "exceeded", "surged", "surge", "record", "upgrade", "upgraded",
    "outperform", "outperformed", "raised", "raise", "growth", "grew", "accelerat",
    "strong", "strength", "robust", "momentum", "breakout", "bullish", "rally",
    "partnership", "deal", "contract", "win", "won", "expand", "expansion",
    "profit", "profitable", "margin", "guidance", "upside", "positive", "approved",
    "launch", "launched", "gain", "gains", "higher", "above", "ahead",
}

BEARISH_WORDS = {
    "miss", "missed", "fell", "fall", "decline", "declined", "downgrade", "downgraded",
    "underperform", "cut", "cuts", "lowered", "lower", "weak", "weakness", "slowdown",
    "loss", "losses", "layoff", "layoffs", "restructur", "warning", "warn", "cautious",
    "bearish", "below", "disappoint", "disappointing", "concern", "concerns", "risk",
    "lawsuit", "probe", "investigation", "recall", "delay", "delayed", "guidance cut",
    "miss estimates", "revenue miss", "eps miss", "negative", "headwind", "pressure",
}

INTENSIFIERS = {"significantly", "sharply", "heavily", "massively", "deeply", "extremely"}
NEGATORS = {"not", "no", "didn't", "didn't", "wasn't", "won't", "wouldn't", "never", "despite"}


def score_headline(text: str) -> float:
    """Return sentiment score for a single text string in [-1.0, 1.0]."""
    words = text.lower().split()
    tokens = set(words)

    bull = sum(
        1
        for w in words
        if any(w.startswith(bw) for bw in BULLISH_WORDS)
    )
    bear = sum(
        1
        for w in words
        if any(w.startswith(bw) for bw in BEARISH_WORDS)
    )

    # Simple negation: flip polarity if negator appears within 3 tokens of a signal
    negated_bull, negated_bear = 0, 0
    for i, w in enumerate(words):
        window = set(words[max(0, i - 3) : i])
        if any(w.startswith(bw) for bw in BULLISH_WORDS) and window & NEGATORS:
            negated_bull += 1
        if any(w.startswith(bw) for bw in BEARISH_WORDS) and window & NEGATORS:
            negated_bear += 1

    net_bull = bull - negated_bull + negated_bear
    net_bear = bear - negated_bear + negated_bull
    total = net_bull + net_bear

    # Intensifier boost
    if tokens & INTENSIFIERS:
        net_bull = int(net_bull * 1.3) if net_bull > 0 else net_bull
        net_bear = int(net_bear * 1.3) if net_bear > 0 else net_bear

    if total == 0:
        return 0.0
    return round((net_bull - net_bear) / max(1, total), 3)


def score_results(results: list[dict]) -> list[dict]:
    """Add a 'sentiment' field to each search result dict."""
    scored = []
    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}"
        r = dict(r)
        r["sentiment"] = score_headline(text)
        r["sentiment_label"] = (
            "bullish" if r["sentiment"] > 0.1
            else "bearish" if r["sentiment"] < -0.1
            else "neutral"
        )
        scored.append(r)
    return scored


def aggregate_sentiment(results: list[dict]) -> dict:
    """Summarise sentiment across a list of scored search results."""
    scores = [r.get("sentiment", 0.0) for r in results if "sentiment" in r]
    if not scores:
        return {"score": 0.0, "label": "neutral", "n": 0}
    avg = round(sum(scores) / len(scores), 3)
    return {
        "score": avg,
        "label": "bullish" if avg > 0.1 else "bearish" if avg < -0.1 else "neutral",
        "n": len(scores),
        "bullish_count": sum(1 for s in scores if s > 0.1),
        "bearish_count": sum(1 for s in scores if s < -0.1),
    }
