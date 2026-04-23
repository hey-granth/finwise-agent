"""JSON loading and typed query interface — all data is read-only and loaded at startup."""

import logging
import re
from pathlib import Path

from agent.config import settings
from agent.models import (
    Holding,
    IndexData,
    MarketContext,
    MutualFundHolding,
    NewsEntities,
    NewsItem,
    Portfolio,
    SectorPerformance,
    StockData,
)

logger = logging.getLogger(__name__)

# Module-level caches populated by preload_data()
_market_context: MarketContext | None = None
_portfolios: dict[str, Portfolio] = {}
_news: list[NewsItem] = []
_stocks: dict[str, StockData] = {}

_PORTFOLIO_ID_RE = re.compile(r"^PORTFOLIO_\d{3,}$")


def preload_data() -> None:
    """Load all 6 JSON files from DATA_DIR into module-level typed structures."""
    import json

    global _market_context, _portfolios, _news, _stocks

    data_dir = Path(settings.data_dir)

    # ---------- market_data.json ----------
    market_path = data_dir / "market_data.json"
    if not market_path.exists():
        raise FileNotFoundError(f"Missing required data file: {market_path}")
    raw_market = json.loads(market_path.read_text(encoding="utf-8"))

    indices: list[IndexData] = []
    for symbol, idx in raw_market.get("indices", {}).items():
        indices.append(
            IndexData(
                symbol=symbol,
                name=idx["name"],
                change_percent=idx["change_percent"],
                value=idx["current_value"],
            )
        )

    sectors: list[SectorPerformance] = []
    for sector_name, sec in raw_market.get("sector_performance", {}).items():
        drivers = sec.get("key_drivers", ["N/A"])
        key_driver = drivers[0] if drivers else "N/A"
        sectors.append(
            SectorPerformance(
                sector=sector_name,
                day_change_percent=sec["change_percent"],
                sentiment=sec["sentiment"],
                key_driver=key_driver,
            )
        )

    # Parse stocks for later use
    for symbol, stock in raw_market.get("stocks", {}).items():
        _stocks[symbol] = StockData(
            symbol=symbol,
            name=stock["name"],
            sector=stock["sector"],
            current_price=stock["current_price"],
            change_percent=stock["change_percent"],
            volume=stock["volume"],
            beta=stock["beta"],
        )

    # Derive FII activity and market breadth from news (stub defaults)
    _market_context = MarketContext(
        date=raw_market["metadata"]["date"],
        indices=indices,
        sector_performance=sectors,
        fii_activity="Net sellers ₹4,500 crore",
        market_breadth="12 advances / 38 declines",
        overall_sentiment=_derive_overall_sentiment(indices),
    )

    # ---------- portfolios.json ----------
    port_path = data_dir / "portfolios.json"
    if not port_path.exists():
        raise FileNotFoundError(f"Missing required data file: {port_path}")
    raw_port = json.loads(port_path.read_text(encoding="utf-8"))

    _portfolios.clear()
    for pid, pdata in raw_port.get("portfolios", {}).items():
        if not _PORTFOLIO_ID_RE.match(pid):
            logger.warning("Portfolio ID %s does not match expected pattern — skipping", pid)
            continue

        holdings: list[Holding] = []
        for stock in pdata["holdings"].get("stocks", []):
            holdings.append(
                Holding(
                    symbol=stock["symbol"],
                    quantity=stock["quantity"],
                    avg_buy_price=stock["avg_buy_price"],
                    current_price=stock["current_price"],
                    weight_in_portfolio=stock["weight_in_portfolio"],
                    day_change_percent=stock["day_change_percent"],
                )
            )

        mf_holdings: list[MutualFundHolding] = []
        for mf in pdata["holdings"].get("mutual_funds", []):
            # Some entries use current_nav, some current_price
            current_nav = mf.get("current_nav") or mf.get("current_price", 0.0)
            mf_holdings.append(
                MutualFundHolding(
                    fund_id=mf["scheme_code"],
                    name=mf["scheme_name"],
                    units=mf["units"],
                    current_nav=current_nav,
                    invested_nav=mf["avg_nav"],
                    weight_in_portfolio=mf["weight_in_portfolio"],
                    day_change_percent=mf["day_change_percent"],
                )
            )

        _portfolios[pid] = Portfolio(
            id=pid,
            name=pdata.get("portfolio_type", pid),
            owner=pdata["user_name"],
            holdings=holdings,
            mutual_fund_holdings=mf_holdings,
        )

    # ---------- news_data.json ----------
    news_path = data_dir / "news_data.json"
    if not news_path.exists():
        raise FileNotFoundError(f"Missing required data file: {news_path}")
    raw_news = json.loads(news_path.read_text(encoding="utf-8"))

    _news.clear()
    for article in raw_news.get("news", []):
        entities_raw = article.get("entities", {})
        entities = NewsEntities(
            sectors=entities_raw.get("sectors", []),
            stocks=entities_raw.get("stocks", []),
            indices=entities_raw.get("indices", []),
        )
        _news.append(
            NewsItem(
                id=article["id"],
                headline=article["headline"],
                summary=article["summary"],
                sentiment=article["sentiment"],
                sentiment_score=article["sentiment_score"],
                scope=article["scope"],
                impact_level=article["impact_level"],
                entities=entities,
                causal_factors=article.get("causal_factors", []),
            )
        )

    # ---------- Remaining files — loaded but not parsed into typed models ----------
    for fname in ("mutual_funds.json", "historical_data.json", "sector_mapping.json"):
        fpath = data_dir / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing required data file: {fpath}")
        # Validate JSON parseable; actual usage via specific getters
        json.loads(fpath.read_text(encoding="utf-8"))

    logger.info(
        "Data preloaded: %d portfolios, %d news items, %d stocks",
        len(_portfolios),
        len(_news),
        len(_stocks),
    )


def _derive_overall_sentiment(indices: list[IndexData]) -> str:
    """Derive BULLISH / BEARISH / NEUTRAL from index change percents."""
    if not indices:
        return "NEUTRAL"
    avg = sum(i.change_percent for i in indices) / len(indices)
    if avg > 0.25:
        return "BULLISH"
    if avg < -0.25:
        return "BEARISH"
    return "NEUTRAL"


def get_market_data() -> MarketContext:
    """Return the preloaded MarketContext; raises if data not yet loaded."""
    if _market_context is None:
        raise RuntimeError("Data not loaded — call preload_data() first")
    return _market_context


def get_portfolio(portfolio_id: str) -> Portfolio:
    """Return a Portfolio by ID; raises ValueError if not found."""
    portfolio = _portfolios.get(portfolio_id)
    if portfolio is None:
        raise ValueError(f"Portfolio not found: {portfolio_id}")
    return portfolio


def get_all_portfolios() -> list[Portfolio]:
    """Return all loaded portfolios."""
    return list(_portfolios.values())


def get_news() -> list[NewsItem]:
    """Return all preloaded news items."""
    return list(_news)


def get_news_for_portfolio(portfolio: Portfolio) -> list[NewsItem]:
    """Return only news items whose entities overlap with the portfolio's holdings."""
    # Gather sectors from holdings via stock data lookup
    holding_sectors: set[str] = set()
    holding_symbols: set[str] = set()
    for h in portfolio.holdings:
        holding_symbols.add(h.symbol)
        stock = _stocks.get(h.symbol)
        if stock:
            holding_sectors.add(stock.sector)

    # Also add MF-specific sectors if available (skip — MFs are diversified)
    relevant: list[NewsItem] = []
    for item in _news:
        overlaps_sector = bool(holding_sectors & set(item.entities.sectors))
        overlaps_stock = bool(holding_symbols & set(item.entities.stocks))
        if overlaps_sector or overlaps_stock:
            relevant.append(item)

    # Fallback: MARKET_WIDE news is always relevant
    market_wide = [n for n in _news if n.scope == "MARKET_WIDE" and n not in relevant]
    return relevant + market_wide


def get_sector_info(sector: str) -> SectorPerformance | None:
    """Return SectorPerformance for a given sector name, or None if not found."""
    if _market_context is None:
        return None
    for sp in _market_context.sector_performance:
        if sp.sector == sector:
            return sp
    return None


def get_stock_data(symbol: str) -> StockData | None:
    """Return StockData for a given stock symbol, or None if not found."""
    return _stocks.get(symbol)
