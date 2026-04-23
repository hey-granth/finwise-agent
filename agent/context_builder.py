"""Assembles a structured plain-text context block for LLM consumption."""

from agent.models import (
    MarketContext,
    NewsItem,
    Portfolio,
    PortfolioAnalytics,
)

_IMPACT_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
_MAX_NEWS = 8
_MAX_HOLDINGS = 10


def build_reasoning_context(
    portfolio: Portfolio,
    analytics: PortfolioAnalytics,
    market_context: MarketContext,
    relevant_news: list[NewsItem],
) -> str:
    """Produce a structured plain-text block for injection into the LLM reasoning prompt."""
    sections: list[str] = []

    # --- MARKET CONTEXT ---
    index_parts = " | ".join(
        f"{idx.name}: {idx.change_percent:+.2f}%" for idx in market_context.indices
    )
    sections.append(
        f"=== MARKET CONTEXT ({market_context.date}) ===\n"
        f"Overall Sentiment: {market_context.overall_sentiment}\n"
        f"{index_parts}\n"
        f"FII: {market_context.fii_activity} | Breadth: {market_context.market_breadth}"
    )

    # --- SECTOR PERFORMANCE ---
    sector_lines = "\n".join(
        f"{sp.sector}: {sp.day_change_percent:+.2f}% ({sp.sentiment}) — {sp.key_driver}"
        for sp in market_context.sector_performance
    )
    sections.append(f"=== SECTOR PERFORMANCE ===\n{sector_lines}")

    # --- RELEVANT NEWS (top 8 by impact) ---
    sorted_news = sorted(relevant_news, key=lambda n: _IMPACT_ORDER.get(n.impact_level, 9))[
        :_MAX_NEWS
    ]
    news_lines: list[str] = []
    for item in sorted_news:
        sectors_str = ", ".join(item.entities.sectors) if item.entities.sectors else "—"
        stocks_str = ", ".join(item.entities.stocks) if item.entities.stocks else "—"
        causal_str = "; ".join(item.causal_factors[:2]) if item.causal_factors else "N/A"
        news_lines.append(
            f"[{item.impact_level} | {item.scope} | {item.sentiment}] {item.headline}\n"
            f"  Causal factors: {causal_str}\n"
            f"  Affected sectors: {sectors_str} | Stocks: {stocks_str}"
        )
    sections.append("=== RELEVANT NEWS ===\n" + "\n".join(news_lines))

    # --- PORTFOLIO SNAPSHOT ---
    risk_level = analytics.concentration_risk.level
    risk_sectors = ", ".join(analytics.concentration_risk.breached_sectors)
    risk_str = f"{risk_level} — Exposed sectors: {risk_sectors}" if risk_sectors else risk_level

    pnl_sign = "+" if analytics.day_pnl_absolute >= 0 else ""
    sorted_holdings = sorted(portfolio.holdings, key=lambda h: h.weight_in_portfolio, reverse=True)[
        :_MAX_HOLDINGS
    ]
    holding_lines = "\n".join(
        f"  {h.symbol:<12} {h.weight_in_portfolio:>6.2f}%  {h.day_change_percent:+.2f}% today"
        for h in sorted_holdings
    )

    sections.append(
        f"=== PORTFOLIO SNAPSHOT ===\n"
        f"Owner: {portfolio.owner} | "
        f"Total Value: ₹{analytics.total_value:,.0f} | "
        f"Day P&L: {pnl_sign}₹{analytics.day_pnl_absolute:,.0f} "
        f"({pnl_sign}{analytics.day_pnl_percent:.2f}%)\n"
        f"Concentration Risk: {risk_str}\n\n"
        f"Top Holdings:\n{holding_lines}\n\n"
        f"Asset Mix: {analytics.asset_mix.stocks_percent:.0f}% Stocks / "
        f"{analytics.asset_mix.mutual_funds_percent:.0f}% Mutual Funds"
    )

    return "\n\n".join(sections)
