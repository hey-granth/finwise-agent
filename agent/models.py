"""All Pydantic v2 domain models for finwise-agent. No model is defined elsewhere."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockData(BaseModel):
    """Market data for a single equity instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    sector: str
    current_price: float
    change_percent: float
    volume: int
    beta: float


class IndexData(BaseModel):
    """Market data for a broad market index."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    name: str
    change_percent: float
    value: float


class NewsEntities(BaseModel):
    """Entities referenced in a news article."""

    model_config = ConfigDict(frozen=True)

    sectors: list[str] = Field(default_factory=list)
    stocks: list[str] = Field(default_factory=list)
    indices: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    """A single financial news article with sentiment and impact metadata."""

    model_config = ConfigDict(frozen=True)

    id: str
    headline: str
    summary: str
    sentiment: str
    sentiment_score: float
    scope: str
    impact_level: str
    entities: NewsEntities
    causal_factors: list[str] = Field(default_factory=list)

    @field_validator("sentiment_score")
    @classmethod
    def validate_sentiment_score(cls, v: float) -> float:
        """Ensure sentiment_score is within [-1.0, 1.0]."""
        if not (-1.0 <= v <= 1.0):
            raise ValueError(f"sentiment_score must be in [-1.0, 1.0], got {v}")
        return v


class SectorPerformance(BaseModel):
    """Performance metrics and sentiment for a market sector."""

    model_config = ConfigDict(frozen=True)

    sector: str
    day_change_percent: float
    sentiment: str
    key_driver: str


class Holding(BaseModel):
    """A direct equity holding within a portfolio."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    quantity: int
    avg_buy_price: float
    current_price: float
    weight_in_portfolio: float
    day_change_percent: float


class MutualFundHolding(BaseModel):
    """A mutual fund position within a portfolio."""

    model_config = ConfigDict(frozen=True)

    fund_id: str
    name: str
    units: float
    current_nav: float
    invested_nav: float
    weight_in_portfolio: float
    day_change_percent: float


class Portfolio(BaseModel):
    """A complete investment portfolio with stocks and mutual fund holdings."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    owner: str
    holdings: list[Holding] = Field(default_factory=list)
    mutual_fund_holdings: list[MutualFundHolding] = Field(default_factory=list)


class ConcentrationRisk(BaseModel):
    """Sector concentration risk assessment for a portfolio."""

    model_config = ConfigDict(frozen=True)

    level: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    breached_sectors: list[str] = Field(default_factory=list)
    max_sector_exposure: float


class AssetMix(BaseModel):
    """Percentage split between direct stocks and mutual funds."""

    model_config = ConfigDict(frozen=True)

    stocks_percent: float
    mutual_funds_percent: float


class PortfolioAnalytics(BaseModel):
    """Computed analytics for a portfolio snapshot."""

    model_config = ConfigDict(frozen=True)

    portfolio_id: str
    total_value: float
    invested_value: float
    day_pnl_absolute: float
    day_pnl_percent: float
    sector_allocation: dict[str, float]
    concentration_risk: ConcentrationRisk
    asset_mix: AssetMix


class MarketContext(BaseModel):
    """Aggregated market-wide data for a given date."""

    model_config = ConfigDict(frozen=True)

    date: str
    indices: list[IndexData] = Field(default_factory=list)
    sector_performance: list[SectorPerformance] = Field(default_factory=list)
    fii_activity: str
    market_breadth: str
    overall_sentiment: str


class CausalChain(BaseModel):
    """A causal chain linking a news trigger to portfolio impact."""

    model_config = ConfigDict(frozen=True)

    trigger: str
    sector_impact: str
    stock_impact: str
    portfolio_impact: str


class ConflictSignal(BaseModel):
    """A conflicting signal where news sentiment and price action diverge."""

    model_config = ConfigDict(frozen=True)

    stock: str
    news_sentiment: str
    price_action: str
    explanation: str


class ReasoningOutput(BaseModel):
    """Structured causal briefing produced by the reasoning engine LLM."""

    model_config = ConfigDict(frozen=True)

    portfolio_id: str
    briefing: str
    causal_chains: list[CausalChain] = Field(default_factory=list)
    conflict_signals: list[ConflictSignal] = Field(default_factory=list)
    confidence_score: float
    high_impact_signals: list[str] = Field(default_factory=list)

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Ensure confidence_score is within [0.0, 1.0]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_score must be in [0.0, 1.0], got {v}")
        return v


class EvaluationResult(BaseModel):
    """Quality scores for a reasoning output, produced by the evaluator LLM."""

    model_config = ConfigDict(frozen=True)

    reasoning_quality_score: float
    factual_grounding: float
    causal_depth: float
    relevance: float
    justification: str

    @field_validator("reasoning_quality_score", "factual_grounding", "causal_depth", "relevance")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """Ensure all evaluation scores are within [0.0, 10.0]."""
        if not (0.0 <= v <= 10.0):
            raise ValueError(f"Score must be in [0.0, 10.0], got {v}")
        return v


class AgentResponse(BaseModel):
    """Full response returned by the /analyze endpoint."""

    model_config = ConfigDict(frozen=True)

    market_context: MarketContext
    portfolio_analytics: PortfolioAnalytics
    reasoning: ReasoningOutput
    evaluation: EvaluationResult
    trace_id: str
