"""Portfolio analytics — pure computation of P&L, allocation, and risk metrics."""

import logging

from agent.models import (
    AssetMix,
    ConcentrationRisk,
    MarketContext,
    Portfolio,
    PortfolioAnalytics,
)

logger = logging.getLogger(__name__)

_WEIGHT_TOLERANCE = 0.5  # percent


def compute_analytics(portfolio: Portfolio, market_context: MarketContext) -> PortfolioAnalytics:
    """Compute full analytics for a portfolio given current market context."""
    sector_allocation = _compute_sector_allocation(portfolio)
    concentration_risk = _detect_concentration_risk(sector_allocation)
    asset_mix = _compute_asset_mix(portfolio)
    day_pnl_abs, invested_value = _compute_day_pnl(portfolio)

    # Total current value
    stock_value = sum(h.current_price * h.quantity for h in portfolio.holdings)
    mf_value = sum(mf.current_nav * mf.units for mf in portfolio.mutual_fund_holdings)
    total_value = stock_value + mf_value

    day_pnl_pct = (day_pnl_abs / invested_value * 100) if invested_value > 0 else 0.0

    # Validate weights sum to ~100%
    all_weights = [h.weight_in_portfolio for h in portfolio.holdings] + [
        mf.weight_in_portfolio for mf in portfolio.mutual_fund_holdings
    ]
    weight_sum = sum(all_weights)
    if abs(weight_sum - 100.0) > _WEIGHT_TOLERANCE:
        logger.warning(
            "Portfolio %s: weights sum to %.2f%% (expected ~100%%)",
            portfolio.id,
            weight_sum,
        )

    return PortfolioAnalytics(
        portfolio_id=portfolio.id,
        total_value=total_value,
        invested_value=invested_value,
        day_pnl_absolute=day_pnl_abs,
        day_pnl_percent=day_pnl_pct,
        sector_allocation=sector_allocation,
        concentration_risk=concentration_risk,
        asset_mix=asset_mix,
    )


def _compute_sector_allocation(portfolio: Portfolio) -> dict[str, float]:
    """Compute sector allocation percentages from direct stock holdings only."""
    sector_values: dict[str, float] = {}

    stock_value = sum(h.current_price * h.quantity for h in portfolio.holdings)
    mf_value = sum(mf.current_nav * mf.units for mf in portfolio.mutual_fund_holdings)
    total_value = stock_value + mf_value

    if total_value == 0:
        return {}

    # Aggregate stock holdings by sector (import here to avoid circular)
    from agent.data_loader import get_stock_data  # noqa: PLC0415

    for holding in portfolio.holdings:
        stock = get_stock_data(holding.symbol)
        sector = stock.sector if stock else "UNKNOWN"
        value = holding.current_price * holding.quantity
        sector_values[sector] = sector_values.get(sector, 0.0) + value

    # MF holdings are bucketed as their own category
    if mf_value > 0:
        sector_values["MUTUAL_FUNDS"] = mf_value

    return {sector: round(val / total_value * 100, 2) for sector, val in sector_values.items()}


def _detect_concentration_risk(sector_allocation: dict[str, float]) -> ConcentrationRisk:
    """Classify concentration risk based on highest single-sector exposure."""
    if not sector_allocation:
        return ConcentrationRisk(level="NONE", breached_sectors=[], max_sector_exposure=0.0)

    max_exposure = max(sector_allocation.values())

    if max_exposure > 70:
        level: str = "CRITICAL"
    elif max_exposure > 50:
        level = "HIGH"
    elif max_exposure > 40:
        level = "MEDIUM"
    elif max_exposure > 25:
        level = "LOW"
    else:
        level = "NONE"

    breached = [s for s, v in sector_allocation.items() if v > 25]

    return ConcentrationRisk(
        level=level,  # type: ignore[arg-type]
        breached_sectors=breached,
        max_sector_exposure=max_exposure,
    )


def _compute_asset_mix(portfolio: Portfolio) -> AssetMix:
    """Compute the percentage split between direct stocks and mutual funds."""
    stock_value = sum(h.current_price * h.quantity for h in portfolio.holdings)
    mf_value = sum(mf.current_nav * mf.units for mf in portfolio.mutual_fund_holdings)
    total = stock_value + mf_value

    if total == 0:
        return AssetMix(stocks_percent=0.0, mutual_funds_percent=0.0)

    return AssetMix(
        stocks_percent=round(stock_value / total * 100, 2),
        mutual_funds_percent=round(mf_value / total * 100, 2),
    )


def _compute_day_pnl(portfolio: Portfolio) -> tuple[float, float]:
    """Return (day_pnl_absolute, total_invested_value) across all holdings."""
    stock_pnl = sum((h.current_price - h.avg_buy_price) * h.quantity for h in portfolio.holdings)
    mf_pnl = sum(
        (mf.current_nav - mf.invested_nav) * mf.units for mf in portfolio.mutual_fund_holdings
    )

    stock_invested = sum(h.avg_buy_price * h.quantity for h in portfolio.holdings)
    mf_invested = sum(mf.invested_nav * mf.units for mf in portfolio.mutual_fund_holdings)

    return (stock_pnl + mf_pnl, stock_invested + mf_invested)
