"""Tests for data_loader module."""

import pytest

import agent.data_loader as dl


def setup_function() -> None:
    """Reset module state before each test."""
    dl._market_context = None
    dl._portfolios.clear()
    dl._news.clear()
    dl._stocks.clear()


class TestPreloadData:
    def test_preload_succeeds(self) -> None:
        """preload_data completes without raising on valid data directory."""
        dl.preload_data()
        assert dl._market_context is not None
        assert len(dl._portfolios) > 0
        assert len(dl._news) > 0

    def test_portfolios_have_correct_ids(self) -> None:
        """All loaded portfolios match the PORTFOLIO_00N pattern."""
        import re

        dl.preload_data()
        pattern = re.compile(r"^PORTFOLIO_\d{3,}$")
        for pid in dl._portfolios:
            assert pattern.match(pid), f"Portfolio ID {pid!r} does not match pattern"

    def test_all_three_portfolios_loaded(self) -> None:
        """Exactly the 3 known portfolio IDs are loaded."""
        dl.preload_data()
        assert "PORTFOLIO_001" in dl._portfolios
        assert "PORTFOLIO_002" in dl._portfolios
        assert "PORTFOLIO_003" in dl._portfolios


class TestGetPortfolio:
    def test_valid_portfolio_returned(self) -> None:
        """get_portfolio returns a Portfolio for a known ID."""
        dl.preload_data()
        p = dl.get_portfolio("PORTFOLIO_001")
        assert p.id == "PORTFOLIO_001"
        assert p.owner is not None
        assert len(p.holdings) > 0

    def test_invalid_portfolio_raises_value_error(self) -> None:
        """get_portfolio raises ValueError for an unknown ID."""
        dl.preload_data()
        with pytest.raises(ValueError, match="Portfolio not found: PORTFOLIO_999"):
            dl.get_portfolio("PORTFOLIO_999")

    def test_all_three_portfolios_accessible(self) -> None:
        """All 3 portfolio IDs are queryable without error."""
        dl.preload_data()
        for pid in ("PORTFOLIO_001", "PORTFOLIO_002", "PORTFOLIO_003"):
            p = dl.get_portfolio(pid)
            assert p.id == pid


class TestGetNewsForPortfolio:
    def test_returns_only_relevant_news(self) -> None:
        """get_news_for_portfolio returns a subset of all news."""
        dl.preload_data()
        portfolio = dl.get_portfolio("PORTFOLIO_002")  # Banking heavy
        relevant = dl.get_news_for_portfolio(portfolio)
        all_news = dl.get_news()
        assert len(relevant) <= len(all_news)

    def test_banking_portfolio_gets_banking_news(self) -> None:
        """PORTFOLIO_002 (banking heavy) gets banking-related news items."""
        dl.preload_data()
        portfolio = dl.get_portfolio("PORTFOLIO_002")
        relevant = dl.get_news_for_portfolio(portfolio)
        banking_related = [
            n
            for n in relevant
            if "BANKING" in n.entities.sectors or "HDFCBANK" in n.entities.stocks
        ]
        assert len(banking_related) > 0

    def test_market_wide_news_included(self) -> None:
        """MARKET_WIDE news items are always included in relevant news."""
        dl.preload_data()
        portfolio = dl.get_portfolio("PORTFOLIO_001")
        relevant = dl.get_news_for_portfolio(portfolio)
        market_wide = [n for n in relevant if n.scope == "MARKET_WIDE"]
        assert len(market_wide) > 0

    def test_no_news_for_portfolio_without_data(self) -> None:
        """preload_data does not raise even with valid minimal data."""
        dl.preload_data()
        # All 3 portfolios should have some relevant news
        for pid in ("PORTFOLIO_001", "PORTFOLIO_002", "PORTFOLIO_003"):
            p = dl.get_portfolio(pid)
            result = dl.get_news_for_portfolio(p)
            assert isinstance(result, list)


class TestGetMarketData:
    def test_market_context_has_date(self) -> None:
        """get_market_data returns MarketContext with a valid date string."""
        dl.preload_data()
        ctx = dl.get_market_data()
        assert ctx.date == "2026-04-21"
        assert len(ctx.indices) > 0
        assert len(ctx.sector_performance) > 0

    def test_raises_before_preload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_market_data raises RuntimeError if _market_context is None."""
        monkeypatch.setattr(dl, "_market_context", None)
        with pytest.raises(RuntimeError):
            dl.get_market_data()
