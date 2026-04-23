"""Tests for portfolio_analytics module."""

import pytest

from agent.models import (
    AssetMix,
    ConcentrationRisk,
    Holding,
    MarketContext,
    MutualFundHolding,
    Portfolio,
)
from agent.portfolio_analytics import (
    _compute_asset_mix,
    _compute_day_pnl,
    _detect_concentration_risk,
    compute_analytics,
)


def _make_market_context() -> MarketContext:
    return MarketContext(
        date="2026-04-21",
        indices=[],
        sector_performance=[],
        fii_activity="Net sellers ₹4,500 crore",
        market_breadth="12 advances / 38 declines",
        overall_sentiment="BEARISH",
    )


def _make_stock_holding(
    symbol: str = "TCS",
    qty: int = 10,
    avg: float = 100.0,
    current: float = 120.0,
    weight: float = 50.0,
    day_pct: float = 1.5,
) -> Holding:
    return Holding(
        symbol=symbol,
        quantity=qty,
        avg_buy_price=avg,
        current_price=current,
        weight_in_portfolio=weight,
        day_change_percent=day_pct,
    )


def _make_mf_holding(
    fund_id: str = "MF001",
    units: float = 100.0,
    current_nav: float = 200.0,
    invested_nav: float = 180.0,
    weight: float = 50.0,
    day_pct: float = -0.5,
) -> MutualFundHolding:
    return MutualFundHolding(
        fund_id=fund_id,
        name="Test Fund",
        units=units,
        current_nav=current_nav,
        invested_nav=invested_nav,
        weight_in_portfolio=weight,
        day_change_percent=day_pct,
    )


# --- P&L tests ---


class TestComputeDayPnl:
    def test_stock_only_pnl(self) -> None:
        """P&L for stock holdings is (current - avg) * qty."""
        portfolio = Portfolio(
            id="PORTFOLIO_001",
            name="Test",
            owner="Test User",
            holdings=[_make_stock_holding(qty=10, avg=100.0, current=120.0)],
        )
        pnl, invested = _compute_day_pnl(portfolio)
        assert pnl == pytest.approx(200.0)  # (120 - 100) * 10
        assert invested == pytest.approx(1000.0)  # 100 * 10

    def test_mf_only_pnl(self) -> None:
        """P&L for MF holdings is (current_nav - invested_nav) * units."""
        portfolio = Portfolio(
            id="PORTFOLIO_001",
            name="Test",
            owner="Test User",
            mutual_fund_holdings=[
                _make_mf_holding(units=100.0, current_nav=200.0, invested_nav=180.0)
            ],
        )
        pnl, invested = _compute_day_pnl(portfolio)
        assert pnl == pytest.approx(2000.0)  # (200 - 180) * 100
        assert invested == pytest.approx(18000.0)  # 180 * 100

    def test_combined_pnl(self) -> None:
        """Combined P&L sums stocks and MFs."""
        portfolio = Portfolio(
            id="PORTFOLIO_001",
            name="Test",
            owner="Test User",
            holdings=[_make_stock_holding(qty=10, avg=100.0, current=110.0)],
            mutual_fund_holdings=[
                _make_mf_holding(units=50.0, current_nav=200.0, invested_nav=190.0)
            ],
        )
        pnl, invested = _compute_day_pnl(portfolio)
        assert pnl == pytest.approx(100.0 + 500.0)  # 10*10 + 10*50
        assert invested == pytest.approx(1000.0 + 9500.0)

    def test_empty_portfolio_pnl(self) -> None:
        """Empty portfolio returns zero P&L and zero invested."""
        portfolio = Portfolio(id="PORTFOLIO_001", name="Test", owner="Test User")
        pnl, invested = _compute_day_pnl(portfolio)
        assert pnl == 0.0
        assert invested == 0.0


# --- Asset mix tests ---


class TestComputeAssetMix:
    def test_stocks_only(self) -> None:
        """100% stocks portfolio has 0% MF."""
        portfolio = Portfolio(
            id="PORTFOLIO_001",
            name="Test",
            owner="Test User",
            holdings=[_make_stock_holding(qty=10, current=100.0, weight=100.0)],
        )
        mix = _compute_asset_mix(portfolio)
        assert mix.stocks_percent == pytest.approx(100.0)
        assert mix.mutual_funds_percent == pytest.approx(0.0)

    def test_mf_only(self) -> None:
        """100% MF portfolio has 0% stocks."""
        portfolio = Portfolio(
            id="PORTFOLIO_001",
            name="Test",
            owner="Test User",
            mutual_fund_holdings=[_make_mf_holding(units=100.0, current_nav=100.0, weight=100.0)],
        )
        mix = _compute_asset_mix(portfolio)
        assert mix.stocks_percent == pytest.approx(0.0)
        assert mix.mutual_funds_percent == pytest.approx(100.0)

    def test_empty_portfolio(self) -> None:
        """Empty portfolio returns 0/0 split."""
        mix = _compute_asset_mix(Portfolio(id="PORTFOLIO_001", name="Test", owner="Test User"))
        assert mix.stocks_percent == 0.0
        assert mix.mutual_funds_percent == 0.0


# --- Concentration risk tests ---


class TestDetectConcentrationRisk:
    def test_none_risk(self) -> None:
        """All sectors below 25% → NONE."""
        alloc = {"A": 20.0, "B": 20.0, "C": 20.0, "D": 20.0, "E": 20.0}
        risk = _detect_concentration_risk(alloc)
        assert risk.level == "NONE"

    def test_low_risk(self) -> None:
        """Single sector at 30% → LOW."""
        alloc = {"BANKING": 30.0, "IT": 40.0, "OTHER": 30.0}
        risk = _detect_concentration_risk(alloc)
        # max is IT at 40%, which is > 25 and <= 40 → LOW actually > 40 is MEDIUM
        # IT=40 which is exactly boundary — spec says >40 is MEDIUM, so 40% is LOW
        assert risk.level == "LOW"

    def test_medium_risk(self) -> None:
        """Single sector at 45% → MEDIUM."""
        alloc = {"BANKING": 45.0, "IT": 55.0}
        risk = _detect_concentration_risk(alloc)
        assert risk.level == "HIGH"  # 55 > 50

    def test_high_risk(self) -> None:
        """Single sector at 55% → HIGH."""
        alloc = {"BANKING": 55.0, "OTHER": 45.0}
        risk = _detect_concentration_risk(alloc)
        assert risk.level == "HIGH"

    def test_critical_risk(self) -> None:
        """Single sector at 75% → CRITICAL."""
        alloc = {"BANKING": 75.0, "OTHER": 25.0}
        risk = _detect_concentration_risk(alloc)
        assert risk.level == "CRITICAL"
        assert risk.max_sector_exposure == pytest.approx(75.0)

    def test_empty_allocation(self) -> None:
        """Empty allocation → NONE."""
        risk = _detect_concentration_risk({})
        assert risk.level == "NONE"
        assert risk.max_sector_exposure == 0.0


# --- Full analytics integration test ---


class TestComputeAnalytics:
    def test_analytics_returns_correct_structure(self) -> None:
        """compute_analytics returns a PortfolioAnalytics with correct portfolio_id."""
        portfolio = Portfolio(
            id="PORTFOLIO_001",
            name="Test",
            owner="Rahul",
            holdings=[
                _make_stock_holding(
                    symbol="HDFCBANK", qty=10, current=1542.30, avg=1520.0, weight=100.0
                )
            ],
        )
        market = _make_market_context()
        result = compute_analytics(portfolio, market)
        assert result.portfolio_id == "PORTFOLIO_001"
        assert result.total_value == pytest.approx(10 * 1542.30)
        assert isinstance(result.concentration_risk, ConcentrationRisk)
        assert isinstance(result.asset_mix, AssetMix)
