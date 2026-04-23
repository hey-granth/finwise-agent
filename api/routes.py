"""All FastAPI route handlers for finwise-agent."""

import logging

from fastapi import APIRouter, HTTPException

from agent.data_loader import (
    get_all_portfolios,
    get_market_data,
    get_news_for_portfolio,
    get_portfolio,
)
from agent.evaluator import evaluate_reasoning
from agent.models import AgentResponse, MarketContext, PortfolioAnalytics
from agent.portfolio_analytics import compute_analytics
from agent.reasoning_engine import generate_briefing
from agent.tracer import create_trace, flush

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    return {"status": "ok", "version": "0.1.0"}


@router.get("/portfolios")
async def list_portfolios() -> list[dict]:
    """Return all portfolio IDs and owner names."""
    return [{"id": p.id, "owner": p.owner, "name": p.name} for p in get_all_portfolios()]


@router.get("/market")
async def get_market() -> MarketContext:
    """Return the current market context snapshot."""
    return get_market_data()


@router.get("/analyze/{portfolio_id}/analytics")
async def get_analytics(portfolio_id: str) -> PortfolioAnalytics:
    """Return portfolio analytics without any LLM call (fast path)."""
    try:
        portfolio = get_portfolio(portfolio_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

    market = get_market_data()
    return compute_analytics(portfolio, market)


@router.post("/analyze/{portfolio_id}")
async def analyze_portfolio(portfolio_id: str) -> AgentResponse:
    """Run the full agent pipeline: analytics + LLM briefing + evaluation."""
    # 1. Load portfolio
    try:
        portfolio = get_portfolio(portfolio_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

    # 2. Load market context
    market = get_market_data()

    # 3. Compute analytics
    analytics = compute_analytics(portfolio, market)

    # 4. Filter relevant news
    relevant_news = get_news_for_portfolio(portfolio)

    # 5. Create Langfuse trace
    trace = create_trace(name="finwise-analyze", portfolio_id=portfolio_id)

    # 6. Generate causal briefing
    try:
        reasoning = await generate_briefing(portfolio, analytics, market, relevant_news, trace)
    except ValueError as exc:
        logger.exception("Reasoning engine error for portfolio %s", portfolio_id)
        raise HTTPException(status_code=500, detail=f"Reasoning engine error: {exc}") from exc

    # 7. Evaluate reasoning quality
    try:
        evaluation = await evaluate_reasoning(reasoning, analytics, trace)
    except ValueError as exc:
        logger.exception("Evaluator error for portfolio %s", portfolio_id)
        raise HTTPException(status_code=500, detail=f"Reasoning engine error: {exc}") from exc

    # 8. Return full response
    response = AgentResponse(
        market_context=market,
        portfolio_analytics=analytics,
        reasoning=reasoning,
        evaluation=evaluation,
        trace_id=str(trace.id),
    )
    flush()
    return response
