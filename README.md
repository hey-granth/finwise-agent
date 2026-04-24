# finwise-agent

An Autonomous Financial Advisor Agent that doesn't just report data — it reasons through it. The agent ingests market data, news, and portfolio holdings to generate causal explanations of portfolio performance, tracing macro events through sector trends down to individual stock impact.

> **Live Demo:** https://finwise-agent.onrender.com 

> **GitHub:** https://github.com/hey-granth/finwise-agent

---

## Architecture

```
HTTP Request
     │
     ▼
FastAPI (/api/v1/analyze/{portfolio_id})
     │
     ├── data_loader          → Portfolio + MarketContext + News (from JSON)
     ├── portfolio_analytics  → P&L, sector allocation, concentration risk
     ├── market_intelligence  → overall sentiment, top movers
     ├── context_builder      → structured plain-text context for LLM
     ├── reasoning_engine     → Groq LLM → causal briefing (JSON)
     ├── evaluator            → Groq LLM → reasoning quality score (JSON)
     └── tracer               → Langfuse trace for both LLM calls
     │
     ▼
AgentResponse
  ├── market_context       (indices, sectors, FII activity)
  ├── portfolio_analytics  (P&L, allocation, concentration risk)
  ├── reasoning            (briefing, causal chains, conflict signals)
  ├── evaluation           (quality score, justification)
  └── trace_id             (Langfuse trace reference)
```

---

## Project Structure

```
finwise-agent/
├── agent/
│   ├── config.py                # Settings via pydantic-settings
│   ├── models.py                # All Pydantic v2 domain models
│   ├── data_loader.py           # JSON loading + typed query interface
│   ├── market_intelligence.py   # Sentiment aggregation (no LLM)
│   ├── portfolio_analytics.py   # P&L, allocation, risk detection (no LLM)
│   ├── context_builder.py       # Assembles plain-text LLM context
│   ├── reasoning_engine.py      # Groq call — causal briefing generation
│   ├── evaluator.py             # Groq call — reasoning quality scoring
│   └── tracer.py                # Langfuse integration
├── api/
│   ├── main.py                  # FastAPI app + lifespan
│   └── routes.py                # Route handlers
├── data/
│   ├── market_data.json         # 40+ stocks, 5 indices, 10 sectors
│   ├── news_data.json           # 25 articles with sentiment + entity tags
│   ├── portfolios.json          # 3 user portfolio samples
│   ├── mutual_funds.json        # 12 MF schemes with NAV and returns
│   ├── historical_data.json     # 7-day index/stock history, FII/DII data
│   └── sector_mapping.json      # Sector-stock relationships
├── prompts/
│   ├── reasoning.txt            # System prompt for briefing generation
│   └── evaluator.txt            # System prompt for self-evaluation
├── tests/
│   ├── test_portfolio_analytics.py
│   ├── test_market_intelligence.py
│   └── test_data_loader.py
├── Procfile
├── pyproject.toml
└── uv.lock
```

---

## How to Run

### Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Groq API key — [console.groq.com](https://console.groq.com) (free, no card required)
- Langfuse account — [us.cloud.langfuse.com](https://us.cloud.langfuse.com) (free tier)

### Install

```bash
git clone https://github.com/hey-granth/finwise-agent
cd finwise-agent
uv sync
```

### Configure

```bash
cp .env.example .env
```

Fill in `.env`:

```env
GROQ_API_KEY=your_groq_api_key
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
GROQ_MODEL=llama-3.3-70b-versatile
DATA_DIR=./data
LOG_LEVEL=INFO
```

### Start the Server

```bash
uv run uvicorn api.main:app --reload
```

Server runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### Run Tests

```bash
uv run pytest tests/ -v
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/market` | Current market snapshot |
| GET | `/api/v1/portfolios` | List all available portfolios |
| GET | `/api/v1/analyze/{id}/analytics` | Portfolio analytics only — no LLM call |
| POST | `/api/v1/analyze/{id}` | Full agent run — LLM reasoning + evaluation |

---

## Try It

> Replace `http://localhost:8000` with `https://finwise-agent.onrender.com` to hit the live deployment.

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Market Snapshot
```bash
curl http://localhost:8000/api/v1/market
```

### List Portfolios
```bash
curl http://localhost:8000/api/v1/portfolios
```

### Portfolio Analytics (No LLM)
```bash
curl http://localhost:8000/api/v1/analyze/PORTFOLIO_001/analytics
curl http://localhost:8000/api/v1/analyze/PORTFOLIO_002/analytics
curl http://localhost:8000/api/v1/analyze/PORTFOLIO_003/analytics
```

### Full Agent Analysis

**PORTFOLIO_001 — Diversified (Rahul Sharma)**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/PORTFOLIO_001
```
Day P&L ~-0.44% | Concentration risk: NONE | Balanced causal chains across Banking and IT.

**PORTFOLIO_002 — Sector-Concentrated (Priya Patel)**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/PORTFOLIO_002
```
Day P&L ~-2.73% | Concentration risk: CRITICAL (Banking 71.87%) | RBI-driven causal chain | Bajaj Finance conflict signal.

**PORTFOLIO_003 — Conservative (Arun Krishnamurthy)**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/PORTFOLIO_003
```
Day P&L ~-0.04% | Concentration risk: NONE | Minimal signal — defensive MF holdings buffer market impact.

### Pretty-print Any Response
```bash
curl -s -X POST http://localhost:8000/api/v1/analyze/PORTFOLIO_002 | python3 -m json.tool
```

### Edge Case — Invalid Portfolio ID
```bash
curl -X POST http://localhost:8000/api/v1/analyze/PORTFOLIO_999
# Returns: 404 {"detail": "Portfolio not found: PORTFOLIO_999"}
```

---

## Mock Data Inputs

The dataset simulates a **risk-off market day — April 21, 2026**:

- NIFTY 50: -1.00% (Bearish)
- Bank Nifty: -2.33% (RBI hawkish stance)
- NIFTY IT: +1.22% (US tech earnings)
- FII: Net sellers ₹4,500 crore
- Market breadth: 12 advances / 38 declines

### Portfolio Samples

| Portfolio | Type | Day P&L | Concentration Risk |
|---|---|---|---|
| PORTFOLIO_001 | Diversified | ~-0.44% | NONE |
| PORTFOLIO_002 | Banking-heavy | ~-2.73% | CRITICAL |
| PORTFOLIO_003 | Conservative MF-heavy | ~-0.04% | NONE |

### Edge Cases Included

- **Positive news + negative price:** Bajaj Finance — strong guidance but sector headwinds dominate
- **Mixed signals:** ICICI Bank — improved asset quality but NIM compression
- **Sector vs stock divergence:** Tata Motors +0.79% vs Auto sector -1.85% (EV leadership)

---

## Observability

All LLM calls are traced via Langfuse. Each `/analyze` request produces one trace containing two generations:

- `reasoning` — causal briefing generation
- `evaluator` — reasoning quality scoring

The `trace_id` in every API response maps directly to a trace in the Langfuse dashboard at [us.cloud.langfuse.com](https://us.cloud.langfuse.com).

---

## Evaluation Layer

The agent scores its own output after every reasoning call across three dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| Causal depth | 40% | Does the briefing trace causes to effects with specificity? |
| Factual grounding | 35% | Are claims supported by the provided market data? |
| Relevance | 25% | Is the briefing focused on what matters for this portfolio? |

`reasoning_quality_score = 0.4 × causal_depth + 0.35 × factual_grounding + 0.25 × relevance`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.14 |
| Package manager | uv |
| Framework | FastAPI + Pydantic v2 |
| LLM | Groq `llama-3.3-70b-versatile` (free tier) |
| Tracing | Langfuse cloud (free tier) |
| Hosting | Render |