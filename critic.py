"""Critic agent — second LLM pass that stress-tests the researcher's thesis.

Two-agent flow:
  Agent 1 (researcher): gathers data via tools, writes structured thesis
  Agent 2 (critic):     reads thesis, challenges claims, flags overconfidence

Usage:
  from critic import run_full_analysis
  result = run_full_analysis("NVDA", thesis_text)
  print(result["combined"])
"""

import logging

import anthropic
from dotenv import load_dotenv

from prompts.critic import CRITIC_PROMPT

load_dotenv()

client = anthropic.Anthropic()
MODEL = "claude-opus-4-7"

logger = logging.getLogger(__name__)


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
          "thesis": str,       # researcher output
          "critique": str,     # critic output
          "combined": str,     # both joined for display
        }
    """
    critique = run_critic(ticker, thesis)
    combined = f"{thesis}\n\n---\n\n## Analyst Critique\n\n{critique}"
    return {
        "ticker": ticker.upper(),
        "thesis": thesis,
        "critique": critique,
        "combined": combined,
    }
