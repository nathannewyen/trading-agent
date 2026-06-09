"""Tests for the FastAPI endpoints using TestClient."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_version_matches_agent():
    from agent import __version__
    resp = client.get("/health")
    assert resp.json()["version"] == __version__


@patch("api.app.run_agent", return_value="## Thesis\n\nBullish on NVDA.")
def test_research_returns_thesis(mock_run):
    resp = client.post("/research", json={"ticker": "NVDA"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "NVDA"
    assert "thesis" in data
    assert "model" in data


@patch("api.app.run_agent", return_value="## Thesis\n\nBullish on NVDA.")
def test_research_uppercases_ticker(mock_run):
    resp = client.post("/research", json={"ticker": "nvda"})
    assert resp.json()["ticker"] == "NVDA"


def test_research_rejects_digit_only_ticker():
    resp = client.post("/research", json={"ticker": "12345"})
    assert resp.status_code == 422


def test_research_rejects_too_long_ticker():
    resp = client.post("/research", json={"ticker": "TOOLONG"})
    assert resp.status_code == 422


def test_portfolio_rejects_empty_list():
    resp = client.post("/portfolio", json={"tickers": []})
    assert resp.status_code == 422


@patch("portfolio.run_agent", return_value="## Thesis\n**Bias:** Bullish\n**Confidence:** High\n**Sector:** Technology")
def test_portfolio_returns_ranked_results(mock_run):
    resp = client.post("/portfolio", json={"tickers": ["NVDA", "AAPL"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 2
    for r in data["results"]:
        assert "ticker" in r
        assert "score" in r
