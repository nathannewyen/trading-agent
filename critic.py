"""Critic agent — second LLM pass that stress-tests the researcher's thesis.

Two-agent flow:
  Agent 1 (researcher): gathers data via tools, writes structured thesis
  Agent 2 (critic):     reads thesis, challenges claims, flags overconfidence

Usage:
  from critic import run_full_analysis
  result = run_full_analysis("NVDA", thesis_text)
  print(result["combined"])
  print(result["confidence_score"])  # 0.0 – 1.0 composite
"""

import logging
import re

import anthropic
from dotenv import load_dotenv

from config import MODEL
from prompts.critic import CRITIC_PROMPT

load_dotenv()

client = anthropic.Anthropic()

logger = logging.getLogger(__name__)

# Confidence level mapping
_CONFIDENCE_MAP = {"High": 1.0, "Medium": 0.5, "Low": 0.0}

_RESEARCHER_CONFIDENCE_RE = re.compile(
    r"\*\*Confidence:\*\*\s*(High|Medium|Low)", re.IGNORECASE
)
_CRITIC_ADJUSTED_RE = re.compile(
    r"\*\*Adjusted Confidence:\*\*\s*(Higher|Same|Lower)", re.IGNORECASE
)
_VERDICT_RE = re.compile(
    r"\*\*Verdict:\*\*\s*(Thesis Stands|Weakened|Significantly Weakened)", re.IGNORECASE
)


def _extract_confidence_score(thesis: str, critique: str) -> float:
    """Derive a composite 0.0–1.0 confidence score from the thesis and critique.

    Logic:
      1. Start from researcher's stated confidence level.
      2. Apply critic's adjustment direction (+0.15 / 0 / -0.15).
      3. Apply verdict penalty (Weakened: -0.1, Significantly Weakened: -0.25).
    """
    # Researcher's base confidence
    rc_match = _RESEARCHER_CONFIDENCE_RE.search(thesis)
    base = _CONFIDENCE_MAP.get(rc_match.group(1).capitalize(), 0.5) if rc_match else 0.5

    # Critic adjustment
    adj_match = _CRITIC_ADJUSTED_RE.search(critique)
    if adj_match:
        adj = adj_match.group(1).lower()
        if adj == "higher":
            base = min(1.0, base + 0.15)
        elif adj == "lower":
            base = max(0.0, base - 0.15)

    # Verdict penalty
    verdict_match = _VERDICT_RE.search(critique)
    if verdict_match:
        verdict = verdict_match.group(1).lower()
        if "significantly" in verdict:
            base = max(0.0, base - 0.25)
        elif "weakened" in verdict:
            base = max(0.0, base - 0.10)

    return round(base, 3)


def run_critic(ticker: str, thesis: str) -> str:
    """Single critic agent call. Returns critique as markdown string."""
    logger.info(f"Running critic agent for {ticker.upper()}")
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=CRITIC_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Stress-test this trade thesis for {ticker.upper()}. "
                    f"Be specific — quote exact claims and numbers.\n\n{thesis}"
                ),
            }
        ],
    )
    return response.content[0].text


def run_full_analysis(ticker: str, thesis: str) -> dict:
    """
    Two-agent analysis: researcher thesis + critic challenge.

    Returns:
        {
          "ticker": str,
          "thesis": str,             # researcher output
          "critique": str,           # critic output
          "combined": str,           # both joined for display
          "confidence_score": float, # 0.0–1.0 composite from both agents
        }
    """
    critique = run_critic(ticker, thesis)
    combined = f"{thesis}\n\n---\n\n## Analyst Critique\n\n{critique}"
    confidence_score = _extract_confidence_score(thesis, critique)
    return {
        "ticker": ticker.upper(),
        "thesis": thesis,
        "critique": critique,
        "combined": combined,
        "confidence_score": confidence_score,
    }
