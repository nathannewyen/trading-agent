"""Pydantic request/response models for the trading research API."""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=6, description="Stock ticker symbol")
    question: str | None = Field(None, description="Custom research question (optional)")
    sector: str | None = Field(None, description="Sector lens: tech, energy, financials, healthcare, consumer")
    no_cache: bool = Field(False, description="Bypass disk cache for fresh data")


class ResearchResponse(BaseModel):
    ticker: str
    thesis: str
    model: str


class CompareRequest(BaseModel):
    ticker_a: str = Field(..., min_length=1, max_length=6)
    ticker_b: str = Field(..., min_length=1, max_length=6)
    quick: bool = Field(False, description="Use earnings snapshot only (faster)")


class CompareResponse(BaseModel):
    ticker_a: str
    ticker_b: str
    comparison: str


class PortfolioRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1, description="List of ticker symbols")
    no_cache: bool = Field(False)


class PortfolioResult(BaseModel):
    ticker: str
    score: float
    bias: str
    confidence: str
    sector: str


class PortfolioResponse(BaseModel):
    results: list[PortfolioResult]


class HealthResponse(BaseModel):
    status: str
    version: str
