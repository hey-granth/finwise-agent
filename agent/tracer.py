"""Langfuse tracing setup — never propagates exceptions to callers."""

import logging

from langfuse import Langfuse
from langfuse.client import StatefulTraceClient

from agent.config import settings

logger = logging.getLogger(__name__)

_langfuse_client: Langfuse | None = None


def get_langfuse_client() -> Langfuse:
    """Return the singleton Langfuse client, initializing it if needed."""
    global _langfuse_client
    if _langfuse_client is None:
        try:
            _langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        except Exception:
            logger.exception("Failed to initialize Langfuse client")
            # Return a stub that won't break callers
            _langfuse_client = Langfuse(
                public_key="stub",
                secret_key="stub",
                host="https://us.cloud.langfuse.com",
            )
    return _langfuse_client


def create_trace(name: str, portfolio_id: str) -> StatefulTraceClient:
    """Create and return a new Langfuse trace for the given name and portfolio."""
    try:
        client = get_langfuse_client()
        trace = client.trace(name=name, metadata={"portfolio_id": portfolio_id})
        return trace
    except Exception:
        logger.exception("Failed to create Langfuse trace — using fallback")
        # Return a no-op trace object
        client = get_langfuse_client()
        return client.trace(name="fallback", metadata={})


def log_generation(
    trace: StatefulTraceClient,
    name: str,
    prompt: str,
    completion: str,
    model: str,
    usage: dict,
) -> None:
    """Log a single LLM generation to the given trace. Never raises."""
    try:
        trace.generation(
            name=name,
            input=prompt,
            output=completion,
            model=model,
            usage=usage,
        )
    except Exception:
        logger.exception("Failed to log generation '%s' to Langfuse", name)
