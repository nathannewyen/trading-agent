"""Braintrust eval suite for the Trading Research Agent.

Scorers:
  thesis_coherence    — all required sections present (0-1)
  data_grounding      — specific numbers vs vague language (0-1)
  has_recommendation  — actionable rec with bias/entry/target/stop (0-1)
  risk_quality        — bear case has concrete, specific risks (0-1)
  catalyst_recency    — catalysts reference recent quarters or dates (0-1)

Run:
  python evals/run_evals.py
  python evals/run_evals.py --limit 5     # dev smoke test
  python evals/run_evals.py --tag v2      # label a run for comparison
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import braintrust

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import run_agent  # noqa: E402

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "dataset.json"

REQUIRED_SECTIONS = [
    "Company Snapshot",
    "Earnings Analysis",
    "Recent Catalysts",
    "Bull Case",
    "Bear Case",
    "Trade Recommendation",
]

NUMBER_PATTERNS = [
    r"\$[\d,.]+",     # dollar amounts
    r"[\d.]+%",       # percentages
    r"[\d.]+x\b",     # multiples
    r"Q[1-4] \d{4}",  # quarter refs
]

VAGUE_PHRASES = [
    "strong growth",
    "significant increase",
    "notable decline",
    "considerable",
    "robust performance",
    "impressive results",
]

REC_PATTERNS = {
    "has_bias": re.compile(r"\b(Bullish|Bearish|Neutral)\b"),
    "has_entry": re.compile(r"Entry.{0,30}\$[\d.]+"),
    "has_target": re.compile(r"(Price Target|Target).{0,30}\$[\d.]+"),
    "has_stop": re.compile(r"Stop.{0,30}\$[\d.]+"),
    "has_confidence": re.compile(r"\*\*Confidence:\*\*\s*(High|Medium|Low)"),
}

# Markers of concrete risk (not generic)
CONCRETE_RISK_PATTERNS = [
    re.compile(r"\d+%"),                   # percentage cited in risk
    re.compile(r"\$[\d,.]+"),              # dollar amount in risk
    re.compile(r"Q[1-4] \d{4}"),          # quarter reference in risk
    re.compile(r"\b(if|when|should)\b", re.IGNORECASE),  # conditional framing
]

RECENCY_PATTERNS = [
    re.compile(r"Q[1-4] 202[4-6]"),       # recent quarters
    re.compile(r"202[4-6]"),              # recent years
    re.compile(r"\b(recent|latest|this (week|month|quarter|year))\b", re.IGNORECASE),
]


def thesis_coherence(output: str, expected: dict, **_) -> dict:
    present = [s for s in REQUIRED_SECTIONS if s in output]
    missing = [s for s in REQUIRED_SECTIONS if s not in output]
    return {
        "score": len(present) / len(REQUIRED_SECTIONS),
        "metadata": {"present": present, "missing": missing},
    }


def data_grounding(output: str, expected: dict, **_) -> dict:
    total = sum(len(re.findall(p, output)) for p in NUMBER_PATTERNS)
    vague = sum(output.lower().count(p) for p in VAGUE_PHRASES)
    raw = min(1.0, total / 15) - (vague * 0.05)
    return {
        "score": max(0.0, min(1.0, raw)),
        "metadata": {"data_points": total, "vague_phrases": vague},
    }


def has_recommendation(output: str, expected: dict, **_) -> dict:
    checks = {name: bool(pat.search(output)) for name, pat in REC_PATTERNS.items()}
    return {
        "score": sum(checks.values()) / len(checks),
        "metadata": checks,
    }


def risk_quality(output: str, expected: dict, **_) -> dict:
    """Checks whether the Bear Case section has specific, data-backed risks."""
    bear_match = re.search(r"## 5\. Bear Case(.*?)(?=## 6\.|$)", output, re.DOTALL)
    if not bear_match:
        return {"score": 0.0, "metadata": {"bear_case_found": False}}

    bear_text = bear_match.group(1)
    bullet_count = len(re.findall(r"^-\s", bear_text, re.MULTILINE))
    concrete_hits = sum(bool(p.search(bear_text)) for p in CONCRETE_RISK_PATTERNS)

    # Need at least 3 bullets, ideally with concrete data
    bullet_score = min(1.0, bullet_count / 3)
    concrete_score = min(1.0, concrete_hits / len(CONCRETE_RISK_PATTERNS))
    score = (bullet_score * 0.5) + (concrete_score * 0.5)

    return {
        "score": round(score, 3),
        "metadata": {"bullet_count": bullet_count, "concrete_patterns": concrete_hits},
    }


def catalyst_recency(output: str, expected: dict, **_) -> dict:
    """Checks whether catalysts reference recent time periods (not just generic claims)."""
    catalyst_match = re.search(r"## 3\. Recent Catalysts(.*?)(?=## 4\.|$)", output, re.DOTALL)
    if not catalyst_match:
        return {"score": 0.0, "metadata": {"catalysts_found": False}}

    cat_text = catalyst_match.group(1)
    hits = sum(bool(p.search(cat_text)) for p in RECENCY_PATTERNS)
    score = min(1.0, hits / len(RECENCY_PATTERNS))

    return {
        "score": round(score, 3),
        "metadata": {"recency_signals": hits},
    }


def run_task(input_data: dict) -> str:
    return run_agent(input_data["ticker"], input_data.get("question"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Braintrust evals for trading-agent")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases")
    parser.add_argument("--tag", default="v1", help="Label this eval run (e.g. v1, v2-prompt-fix)")
    args = parser.parse_args()

    with open(DATASET_PATH) as fh:
        dataset = json.load(fh)

    if args.limit:
        dataset = dataset[: args.limit]

    print(f"Running {len(dataset)} eval case(s) — tag: {args.tag}\n")

    braintrust.Eval(
        name="trading-research-agent",
        data=dataset,
        task=run_task,
        scores=[
            thesis_coherence,
            data_grounding,
            has_recommendation,
            risk_quality,
            catalyst_recency,
        ],
        metadata={
            "model": "claude-opus-4-7",
            "version": args.tag,
            "tools": ["web_search", "get_earnings", "get_technicals", "get_options", "calculate"],
            "dataset_size": len(dataset),
        },
    )


if __name__ == "__main__":
    main()
