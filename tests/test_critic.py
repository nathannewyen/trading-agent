import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


DUMMY_THESIS = """
### AAPL — Apple Inc.
**Date:** 2025-06-01
**Sector:** Technology | **Industry:** Consumer Electronics

## 1. Company Snapshot
Apple designs and sells consumer electronics. Its ecosystem lock-in drives high margins.

## 2. Earnings Analysis
| Metric | Value | Trend |
|--------|-------|-------|
| Revenue (TTM) | $385B | +6% YoY |
| EPS (TTM) | $6.42 | +8% YoY |

## 3. Recent Catalysts
**News Sentiment:** 3/5 articles bullish
- Q2 2025 earnings beat by $0.12 EPS (May 2025)

## 4. Bull Case
- Services revenue growing 14% YoY
- $110B buyback authorized

## 5. Bear Case
- China revenue declined 8% in Q2 2025
- iPhone unit growth stalled at 1%

## 6. Trade Recommendation
- **Bias:** Bullish
- **Entry Zone:** $195 – $205
- **Price Target:** $240 (12 months)
- **Stop Loss:** $185
- **Confidence:** Medium

## 7. Key Risks to Monitor
- US-China trade escalation
"""

_MOCK_CRITIQUE = "The thesis is well-structured. However, valuation looks stretched at current multiples."


def _make_mock_response(text: str):
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


@patch("critic.client")
def test_run_full_analysis_returns_expected_keys(mock_client):
    from critic import run_full_analysis
    mock_client.messages.create.return_value = _make_mock_response(_MOCK_CRITIQUE)
    result = run_full_analysis("AAPL", DUMMY_THESIS)
    assert set(result.keys()) == {"ticker", "thesis", "critique", "combined", "confidence_score"}
    assert result["ticker"] == "AAPL"
    assert len(result["thesis"]) > 10
    assert len(result["critique"]) > 10
    assert result["combined"] == result["thesis"] + "\n\n---\n\n## Analyst Critique\n\n" + result["critique"]


@patch("critic.client")
def test_confidence_score_is_float_in_range(mock_client):
    from critic import run_full_analysis
    dummy = "## 5. Bear Case\n- Risk A\n## 6. Trade Recommendation\n- **Bias:** Neutral\n- **Confidence:** Low"
    mock_client.messages.create.return_value = _make_mock_response("The thesis is weak and lacks data.")
    result = run_full_analysis("TSLA", dummy)
    score = result["confidence_score"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
