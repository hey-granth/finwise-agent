"""Reasoning engine — calls Groq LLM to generate a causal portfolio briefing."""

import json
import logging
from pathlib import Path

from groq import AsyncGroq
from langfuse.client import StatefulTraceClient

from agent.config import settings
from agent.context_builder import build_reasoning_context
from agent.models import (
    CausalChain,
    ConflictSignal,
    MarketContext,
    Portfolio,
    PortfolioAnalytics,
    ReasoningOutput,
)
from agent.tracer import log_generation

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT: str | None = None


def _get_system_prompt() -> str:
    """Load and cache the reasoning system prompt from disk."""
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = Path("prompts/reasoning.txt").read_text(encoding="utf-8")
    return _SYSTEM_PROMPT


async def _call_groq(
    client: AsyncGroq,
    messages: list[dict],
) -> tuple[str, dict]:
    """Make a single Groq API call and return (content, usage_dict)."""
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.3,
        max_tokens=2048,
    )
    content = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    }
    return content, usage


def _parse_reasoning_json(raw: str, portfolio_id: str) -> ReasoningOutput:
    """Parse LLM response JSON into ReasoningOutput; raises ValueError on failure."""
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data = json.loads(cleaned)
    # Inject portfolio_id if the model omitted it
    data.setdefault("portfolio_id", portfolio_id)

    # Coerce nested dicts to typed models
    causal_chains = [CausalChain(**c) for c in data.get("causal_chains", [])]
    conflict_signals = [ConflictSignal(**c) for c in data.get("conflict_signals", [])]

    return ReasoningOutput(
        portfolio_id=data["portfolio_id"],
        briefing=data["briefing"],
        causal_chains=causal_chains,
        conflict_signals=conflict_signals,
        confidence_score=float(data["confidence_score"]),
        high_impact_signals=data.get("high_impact_signals", []),
    )


async def generate_briefing(
    portfolio: Portfolio,
    analytics: PortfolioAnalytics,
    market_context: MarketContext,
    relevant_news: list,
    trace: StatefulTraceClient,
) -> ReasoningOutput:
    """Generate a causal portfolio briefing via Groq, with one retry on JSON failure."""
    system_prompt = _get_system_prompt()
    user_message = build_reasoning_context(portfolio, analytics, market_context, relevant_news)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    client = AsyncGroq(api_key=settings.groq_api_key)
    raw_content, usage = await _call_groq(client, messages)

    log_generation(
        trace,
        name="reasoning_engine",
        prompt=user_message,
        completion=raw_content,
        model=settings.groq_model,
        usage=usage,
    )

    try:
        return _parse_reasoning_json(raw_content, portfolio.id)
    except (json.JSONDecodeError, KeyError, ValueError) as first_err:
        logger.warning("Reasoning engine: first JSON parse failed (%s) — retrying", first_err)

    # Retry with correction instruction
    messages.append({"role": "assistant", "content": raw_content})
    messages.append(
        {
            "role": "user",
            "content": (
                "Your previous response was not valid JSON or had missing fields. "
                "Return ONLY the JSON object with all required fields. No markdown, no extra text."
            ),
        }
    )

    raw_retry, usage_retry = await _call_groq(client, messages)

    log_generation(
        trace,
        name="reasoning_engine_retry",
        prompt="[retry]",
        completion=raw_retry,
        model=settings.groq_model,
        usage=usage_retry,
    )

    try:
        return _parse_reasoning_json(raw_retry, portfolio.id)
    except (json.JSONDecodeError, KeyError, ValueError) as second_err:
        logger.exception("Reasoning engine failed after retry: %s", second_err)
        raise ValueError("Reasoning engine failed to return valid JSON after retry") from second_err
