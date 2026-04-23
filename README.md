# finwise-agent

An **Autonomous Financial Advisor Agent** that ingests mock market/news/portfolio data, computes analytics, runs an LLM-powered causal reasoning layer (Groq), traces all LLM calls via Langfuse, and self-evaluates output quality.

---

## Architecture

```
Request
  │
  ▼
FastAPI (/analyze/{id})
  │
  ├── data_loader         → load Portfolio + MarketContext + News
  ├── portfolio_analytics → P&L, sector allocation, concentration risk
  ├── market_intelligence → sentiment, top movers
  ├── context_builder     → assemble plain-text LLM context
  ├── reasoning_engine    → Groq LLM → causal briefing (JSON)
  ├── evaluator           → Groq LLM → quality score (JSON)
  └── tracer              → Langfuse trace for both LLM calls
  │
  ▼
AgentResponse (briefing + analytics + evaluation + trace_id)
```

---

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 1. Clone and install

```bash
git clone https://github.com/hey-granth/finwise-agent
cd finwise-agent
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual keys
```

**Get your Groq API key:** https://console.groq.com → API Keys → Create Key

**Get your Langfuse keys:** https://cloud.langfuse.com → Settings → API Keys

### 3. Run locally

```bash
uv run uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

---

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "version": "0.1.0"}
```

### List Portfolios

```bash
curl http://localhost:8000/api/v1/portfolios
# → [{"id": "PORTFOLIO_001", "owner": "Rahul Sharma", "name": "DIVERSIFIED"}, ...]
```

### Current Market Snapshot

```bash
curl http://localhost:8000/api/v1/market
```

### Portfolio Analytics (fast, no LLM)

```bash
curl http://localhost:8000/api/v1/analyze/PORTFOLIO_001/analytics
```

### Full Analysis (LLM briefing + evaluation)

```bash
curl -X POST http://localhost:8000/api/v1/analyze/PORTFOLIO_002
```

Returns `AgentResponse` with:
- `market_context` — current index and sector data
- `portfolio_analytics` — P&L, allocation, risk level
- `reasoning` — causal briefing from Groq LLM
- `evaluation` — quality scores from second LLM call
- `trace_id` — Langfuse trace ID for observability

---

## Running Tests

```bash
uv run pytest
```

Test coverage includes:
- Portfolio P&L computation for all 3 fixture portfolios
- Concentration risk detection at all 5 thresholds (NONE → CRITICAL)
- Asset mix computation
- Market sentiment for bullish/bearish/neutral scenarios
- Top sector mover extraction
- Data loader with all 3 portfolios
- News relevance filtering
- Error handling (`ValueError` on unknown portfolio IDs)

---

## Deploying to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub Repo
3. Set the following environment variables in Railway's Variables tab:
   ```
   GROQ_API_KEY=...
   LANGFUSE_PUBLIC_KEY=...
   LANGFUSE_SECRET_KEY=...
   LANGFUSE_HOST=https://cloud.langfuse.com
   GROQ_MODEL=llama-3.3-70b-versatile
   DATA_DIR=./data
   LOG_LEVEL=INFO
   ```
4. Set the start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Deploy

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.14 |
| Package manager | uv |
| Web framework | FastAPI + Uvicorn |
| LLM provider | Groq (`llama-3.3-70b-versatile`) |
| Observability | Langfuse cloud (free tier) |
| Data validation | Pydantic v2 |
| Configuration | pydantic-settings |
| Linting | ruff |
| Testing | pytest + pytest-asyncio |
| Hosting | Railway (free tier) |
