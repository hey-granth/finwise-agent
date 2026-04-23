"""FastAPI application entry point with lifespan data preloading."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Preload all JSON data at startup; no teardown required."""
    from agent.data_loader import preload_data

    logger.info("Preloading data...")
    preload_data()
    logger.info("Data preloaded successfully.")
    yield


app = FastAPI(
    title="finwise-agent",
    description="Autonomous Financial Advisor Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
