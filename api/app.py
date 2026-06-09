"""FastAPI application for the Trading Research Agent.

Exposes the research pipeline as a REST API so it can be called
from other services, notebooks, or browser-based dashboards.

Run locally:
    uvicorn api.app:app --reload --port 8000

Endpoints:
    GET  /health           — liveness check
    POST /research         — run full research pipeline
    POST /compare          — side-by-side stock comparison
    POST /portfolio        — rank multiple tickers by thesis quality
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent import __version__, run_agent
from config import MODEL
from api.middleware import RateLimitMiddleware
from api.models import (
    CompareRequest,
    CompareResponse,
    HealthResponse,
    PortfolioRequest,
    PortfolioResponse,
    PortfolioResult,
    ResearchRequest,
    ResearchResponse,
)

app = FastAPI(
    title="Trading Research Agent API",
    description="Agentic equity research powered by Anthropic tool use",
    version=__version__,
)

app.add_middleware(RateLimitMiddleware, max_rpm=10)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.post("/research", response_model=ResearchResponse, tags=["research"])
def research(req: ResearchRequest) -> ResearchResponse:
    """Run the full agentic research pipeline for a single ticker."""
    ticker = req.ticker.strip().upper()
    if not ticker or ticker.isdigit() or len(ticker) > 6:
        raise HTTPException(status_code=422, detail=f"Invalid ticker: {req.ticker!r}")

    if req.no_cache:
        from tools import cache as _cache
        _cache.clear_all()

    thesis = run_agent(ticker, question=req.question, sector=req.sector)
    return ResearchResponse(ticker=ticker, thesis=thesis, model=MODEL)


@app.post("/compare", response_model=CompareResponse, tags=["research"])
def compare(req: CompareRequest) -> CompareResponse:
    """Research two tickers and produce a side-by-side comparison."""
    from compare import compare_stocks
    result = compare_stocks(req.ticker_a, req.ticker_b, quick=req.quick)
    return CompareResponse(
        ticker_a=result["ticker_a"],
        ticker_b=result["ticker_b"],
        comparison=result["comparison"],
    )


@app.post("/portfolio", response_model=PortfolioResponse, tags=["research"])
def portfolio(req: PortfolioRequest) -> PortfolioResponse:
    """Research and rank a list of tickers by thesis quality score."""
    from portfolio import run_portfolio
    results = run_portfolio(req.tickers, no_cache=req.no_cache)
    return PortfolioResponse(
        results=[
            PortfolioResult(
                ticker=r["ticker"],
                score=r["score"],
                bias=r["bias"],
                confidence=r["confidence"],
                sector=r.get("sector", "—"),
            )
            for r in results
        ]
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})
