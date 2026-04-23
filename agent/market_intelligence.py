"""Pure computation module for market-level intelligence — no LLM calls."""

from agent.models import MarketContext, SectorPerformance


def compute_market_sentiment(market_context: MarketContext) -> str:
    """Return BULLISH, BEARISH, or NEUTRAL based on index movements and market breadth."""
    index_avg = (
        sum(i.change_percent for i in market_context.indices) / len(market_context.indices)
        if market_context.indices
        else 0.0
    )

    # Parse breadth: "12 advances / 38 declines"
    advance_count = 0
    decline_count = 0
    breadth = market_context.market_breadth
    parts = breadth.replace(",", "").split()
    for i, part in enumerate(parts):
        if part == "advances" and i > 0 and parts[i - 1].isdigit():
            advance_count = int(parts[i - 1])
        if part == "declines" and i > 0 and parts[i - 1].isdigit():
            decline_count = int(parts[i - 1])

    breadth_ratio = (
        advance_count / (advance_count + decline_count)
        if (advance_count + decline_count) > 0
        else 0.5
    )

    if index_avg > 0.5 and breadth_ratio > 0.55:
        return "BULLISH"
    if index_avg < -0.5 or breadth_ratio < 0.35:
        return "BEARISH"
    return "NEUTRAL"


def get_top_movers(market_context: MarketContext, n: int = 3) -> dict[str, list[SectorPerformance]]:
    """Return the top n sector gainers and losers by day_change_percent."""
    sorted_sectors = sorted(
        market_context.sector_performance,
        key=lambda sp: sp.day_change_percent,
        reverse=True,
    )
    gainers = [sp for sp in sorted_sectors if sp.day_change_percent > 0][:n]
    losers = [sp for sp in reversed(sorted_sectors) if sp.day_change_percent < 0][:n]
    return {"gainers": gainers, "losers": losers}


def summarize_fii_activity(market_context: MarketContext) -> str:
    """Return a human-readable summary of FII net activity from market context."""
    return f"FII activity: {market_context.fii_activity}"
