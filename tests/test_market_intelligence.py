"""Tests for market_intelligence module."""

from agent.market_intelligence import (
    compute_market_sentiment,
    get_top_movers,
    summarize_fii_activity,
)
from agent.models import IndexData, MarketContext, SectorPerformance


def _make_market_context(
    index_changes: list[float],
    breadth: str = "30 advances / 20 declines",
    fii: str = "Net buyers ₹1,000 crore",
    sector_changes: list[float] | None = None,
) -> MarketContext:
    indices = [
        IndexData(symbol=f"IDX{i}", name=f"Index {i}", change_percent=c, value=10000.0)
        for i, c in enumerate(index_changes)
    ]
    sectors: list[SectorPerformance] = []
    if sector_changes:
        for i, c in enumerate(sector_changes):
            sentiment = "BULLISH" if c > 0 else "BEARISH" if c < 0 else "NEUTRAL"
            sectors.append(
                SectorPerformance(
                    sector=f"SECTOR{i}",
                    day_change_percent=c,
                    sentiment=sentiment,
                    key_driver="Test driver",
                )
            )
    return MarketContext(
        date="2026-04-21",
        indices=indices,
        sector_performance=sectors,
        fii_activity=fii,
        market_breadth=breadth,
        overall_sentiment="NEUTRAL",
    )


class TestComputeMarketSentiment:
    def test_bullish_scenario(self) -> None:
        """Strong positive indices + good breadth → BULLISH."""
        ctx = _make_market_context([1.5, 2.0, 1.8], breadth="40 advances / 10 declines")
        assert compute_market_sentiment(ctx) == "BULLISH"

    def test_bearish_scenario_indices(self) -> None:
        """Strong negative indices → BEARISH."""
        ctx = _make_market_context([-1.5, -2.0, -1.8], breadth="10 advances / 40 declines")
        assert compute_market_sentiment(ctx) == "BEARISH"

    def test_bearish_scenario_breadth_only(self) -> None:
        """Bad breadth alone can produce BEARISH even with flat indices."""
        ctx = _make_market_context([0.1, 0.0, -0.1], breadth="5 advances / 45 declines")
        assert compute_market_sentiment(ctx) == "BEARISH"

    def test_neutral_scenario(self) -> None:
        """Mixed signals → NEUTRAL."""
        ctx = _make_market_context([0.2, -0.1, 0.3], breadth="25 advances / 25 declines")
        assert compute_market_sentiment(ctx) == "NEUTRAL"

    def test_no_indices(self) -> None:
        """Empty indices list → NEUTRAL."""
        ctx = MarketContext(
            date="2026-04-21",
            indices=[],
            sector_performance=[],
            fii_activity="N/A",
            market_breadth="0 advances / 0 declines",
            overall_sentiment="NEUTRAL",
        )
        assert compute_market_sentiment(ctx) == "NEUTRAL"


class TestGetTopMovers:
    def test_returns_gainers_and_losers(self) -> None:
        """get_top_movers returns dict with gainers and losers keys."""
        ctx = _make_market_context([], sector_changes=[2.5, -1.5, 1.0, -2.0, 0.5])
        result = get_top_movers(ctx, n=2)
        assert "gainers" in result
        assert "losers" in result
        assert len(result["gainers"]) <= 2
        assert len(result["losers"]) <= 2

    def test_gainers_are_positive(self) -> None:
        """All gainers have positive day_change_percent."""
        ctx = _make_market_context([], sector_changes=[3.0, -1.0, 1.5, -2.5])
        result = get_top_movers(ctx, n=3)
        assert all(sp.day_change_percent > 0 for sp in result["gainers"])

    def test_losers_are_negative(self) -> None:
        """All losers have negative day_change_percent."""
        ctx = _make_market_context([], sector_changes=[3.0, -1.0, 1.5, -2.5])
        result = get_top_movers(ctx, n=3)
        assert all(sp.day_change_percent < 0 for sp in result["losers"])

    def test_top_n_limit(self) -> None:
        """Returns at most n gainers and n losers."""
        ctx = _make_market_context([], sector_changes=[1.0, 2.0, 3.0, -1.0, -2.0, -3.0])
        result = get_top_movers(ctx, n=2)
        assert len(result["gainers"]) == 2
        assert len(result["losers"]) == 2

    def test_empty_sectors(self) -> None:
        """Empty sector list returns empty lists."""
        ctx = _make_market_context([], sector_changes=[])
        result = get_top_movers(ctx, n=3)
        assert result["gainers"] == []
        assert result["losers"] == []


class TestSummarizeFiiActivity:
    def test_returns_fii_string(self) -> None:
        """Returns a string containing the FII activity text."""
        ctx = _make_market_context([], fii="Net sellers ₹4,500 crore")
        summary = summarize_fii_activity(ctx)
        assert "Net sellers ₹4,500 crore" in summary
        assert isinstance(summary, str)
