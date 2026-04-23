"""Evaluator — second LLM call that scores reasoning output quality."""

import json
import logging
from pathlib import Path

from groq import AsyncGroq
from langfuse.client import StatefulTraceClient

from agent.config import settings
from agent.models import EvaluationResult, PortfolioAnalytics, ReasoningOutput
from agent.tracer import log_generation

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT: str | None = None


def _get_system_prompt() -> str:
    """Load and cache the evaluator system prompt from disk."""
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        _SYSTEM_PROMPT = Path("prompts/evaluator.txt").read_text(encoding="utf-8")
    return _SYSTEM_PROMPT


async def _call_groq(client: AsyncGroq, messages: list[dict]) -> tuple[str, dict]:
    """Make a single Groq API call and return (content, usage_dict)."""
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.3,
        max_tokens=512,
    )
    content = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    }
    return content, usage


def _parse_evaluation_json(raw: str) -> EvaluationResult:
    """Parse LLM response JSON into EvaluationResult; raises ValueError on failure."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data = json.loads(cleaned)
    return EvaluationResult(
        reasoning_quality_score=float(data["reasoning_quality_score"]),
        factual_grounding=float(data["factual_grounding"]),
        causal_depth=float(data["causal_depth"]),
        relevance=float(data["relevance"]),
        justification=data["justification"],
    )


async def evaluate_reasoning(
    reasoning: ReasoningOutput,
    analytics: PortfolioAnalytics,
    trace: StatefulTraceClient,
) -> EvaluationResult:
    """Score a ReasoningOutput via a second Groq call, with one retry on JSON failure."""
    system_prompt = _get_system_prompt()
    user_message = reasoning.model_dump_json(indent=2)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    client = AsyncGroq(api_key=settings.groq_api_key)
    raw_content, usage = await _call_groq(client, messages)

    log_generation(
        trace,
        name="evaluator",
        prompt=user_message,
        completion=raw_content,
        model=settings.groq_model,
        usage=usage,
    )

    try:
        return _parse_evaluation_json(raw_content)
    except (json.JSONDecodeError, KeyError, ValueError) as first_err:
        logger.warning("Evaluator: first JSON parse failed (%s) — retrying", first_err)

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
        name="evaluator_retry",
        prompt="[retry]",
        completion=raw_retry,
        model=settings.groq_model,
        usage=usage_retry,
    )

    try:
        return _parse_evaluation_json(raw_retry)
    except (json.JSONDecodeError, KeyError, ValueError) as second_err:
        logger.exception("Evaluator failed after retry: %s", second_err)
        raise ValueError("Reasoning engine failed to return valid JSON after retry") from second_err
