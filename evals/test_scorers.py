"""Unit tests for the 5 eval scorers in run_evals.py.

Tests use synthetic thesis strings so no API calls are needed.
Run with: python -m pytest evals/test_scorers.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.run_evals import (
    thesis_coherence,
    data_grounding,
    has_recommendation,
    risk_quality,
    catalyst_recency,
)

# ---------------------------------------------------------------------------
# Synthetic thesis fixtures
# ---------------------------------------------------------------------------

FULL_THESIS = """
### NVDA — NVIDIA Corporation

## 1. Company Snapshot
NVIDIA dominates AI accelerator market with H100 GPUs driving record revenue in Q2 2025.

## 2. Earnings Analysis
| Metric | Value | Trend |
|--------|-------|-------|
| Revenue (TTM) | $100.0B | +122% YoY |
| EPS (TTM) | $24.89 | +140% YoY |
| Gross Margin | 76% | +8 pp |
| Operating Margin | 55% | +10 pp |
| Forward P/E | 35x | vs sector avg 28x |

**EPS Beat/Miss History:**
- Q2 2025: Est $5.50, Act $6.12, +11.3% beat
- Q1 2025: Est $4.50, Act $5.16, +14.7% beat

## 2b. Technical Setup
| Indicator | Value | Signal |
|-----------|-------|--------|
| RSI(14) | 62 | neutral |
| MACD histogram | 1.23 | bullish |

## 3. Recent Catalysts
**News Sentiment:** 8/10 articles bullish | 1/10 bearish
- Q1 2025 results smashed estimates with $22.1B revenue, +18% above guidance
- Blackwell GPU ramp accelerating, supply tightening heading into Q2 2025

## 4. Bull Case
- Revenue growing 122% YoY driven by data center AI spend
- Gross margin at 76% with pricing power intact
- Total addressable market expanding to $500B by 2028

## 5. Bear Case
- Valuation at 35x forward P/E leaves little room if growth decelerates by 20%
- Export restrictions could cut $8B in China revenue in Q3 2025
- Competition from AMD MI300X gaining share in cloud hyperscaler deployments

## 6. Trade Recommendation
- **Bias:** Bullish
- **Entry Zone:** $900 – $950
- **Price Target:** $1,200 (12 months)
- **Stop Loss:** $820
- **Risk/Reward:** 2.8:1
- **Confidence:** High

## 7. Key Risks to Monitor
- Demand slowdown if hyperscaler capex moderates in Q4 2025
"""

EMPTY_THESIS = ""

PARTIAL_THESIS = """
## 1. Company Snapshot
Apple makes iPhones.

## 5. Bear Case
- Competition from Samsung could hurt market share if pricing premium erodes
"""

NUMBERED_BEAR_THESIS = """
## 5. Bear Case
- Revenue could miss by 10% if macro deteriorates in Q3 2025
- Margins under $50 pressure if component costs rise $5 per unit
- China risk: $15B revenue exposure at risk given current regulatory environment
## 6. Trade Recommendation
**Bias:** Neutral
"""

BOLD_BEAR_THESIS = """
**Bear Case**
- EPS could miss by 15% if ad revenue slows in Q4 2025
- Stock at 28x P/E with deceleration risk to $2.50 EPS
- Competition from TikTok may reduce DAU growth by 5% this quarter
**Trade Recommendation**
**Bias:** Bearish
"""

RECENT_CATALYST_THESIS = """
## 3. Recent Catalysts
- Q2 2025 results released this week — beat by 12%
- Analyst upgrade in latest quarter citing 2025 AI tailwinds
"""

OLD_CATALYST_THESIS = """
## 3. Recent Catalysts
- Company announced a new product line
- Management spoke at a conference about strategy
"""


# ---------------------------------------------------------------------------
# thesis_coherence
# ---------------------------------------------------------------------------

def test_coherence_full_thesis():
    r = thesis_coherence(FULL_THESIS, {})
    assert r["score"] == 1.0


def test_coherence_empty():
    r = thesis_coherence(EMPTY_THESIS, {})
    assert r["score"] == 0.0


def test_coherence_partial():
    r = thesis_coherence(PARTIAL_THESIS, {})
    assert 0.0 < r["score"] < 1.0
    assert "Company Snapshot" in r["metadata"]["present"]


# ---------------------------------------------------------------------------
# data_grounding
# ---------------------------------------------------------------------------

def test_data_grounding_full_thesis():
    r = data_grounding(FULL_THESIS, {})
    assert r["score"] > 0.5


def test_data_grounding_empty():
    r = data_grounding(EMPTY_THESIS, {})
    assert r["score"] == 0.0


def test_data_grounding_penalises_vague_phrases():
    vague = "The company showed strong growth with significant increase in impressive results."
    r = data_grounding(vague, {})
    assert r["metadata"]["vague_phrases"] > 0


# ---------------------------------------------------------------------------
# has_recommendation
# ---------------------------------------------------------------------------

def test_has_recommendation_full():
    r = has_recommendation(FULL_THESIS, {})
    assert r["score"] > 0.7


def test_has_recommendation_empty():
    r = has_recommendation(EMPTY_THESIS, {})
    assert r["score"] == 0.0


def test_has_recommendation_bias_only():
    text = "**Bias:** Bullish"
    r = has_recommendation(text, {})
    assert r["metadata"]["has_bias"] is True
    assert r["metadata"]["has_entry"] is False


# ---------------------------------------------------------------------------
# risk_quality — numbered AND bold headings
# ---------------------------------------------------------------------------

def test_risk_quality_numbered_heading():
    r = risk_quality(NUMBERED_BEAR_THESIS, {})
    assert r["score"] > 0.0
    assert r["metadata"]["bear_case_found"] is not False


def test_risk_quality_bold_heading():
    """Bold **Bear Case** heading must also be matched after the regex fix."""
    r = risk_quality(BOLD_BEAR_THESIS, {})
    assert r["score"] > 0.0


def test_risk_quality_empty():
    r = risk_quality(EMPTY_THESIS, {})
    assert r["score"] == 0.0
    assert r["metadata"]["bear_case_found"] is False


# ---------------------------------------------------------------------------
# catalyst_recency
# ---------------------------------------------------------------------------

def test_catalyst_recency_with_dates():
    r = catalyst_recency(RECENT_CATALYST_THESIS, {})
    assert r["score"] > 0.0


def test_catalyst_recency_no_dates():
    r = catalyst_recency(OLD_CATALYST_THESIS, {})
    # May score low/zero because no Q-references or recent year mentions
    assert 0.0 <= r["score"] <= 1.0


def test_catalyst_recency_full_thesis():
    r = catalyst_recency(FULL_THESIS, {})
    assert r["score"] > 0.0


def test_catalyst_recency_missing_section():
    text = "## 4. Bull Case\nSome bull content"
    r = catalyst_recency(text, {})
    assert r["score"] == 0.0
    assert r["metadata"]["catalysts_found"] is False
