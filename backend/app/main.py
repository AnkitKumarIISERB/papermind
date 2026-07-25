"""PaperMind — AI Research Intelligence Platform."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import engine, Base

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev convenience)."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")

    yield

    await engine.dispose()
    logger.info("Database engine disposed.")


app = FastAPI(
    title="PaperMind API",
    description=(
        "AI Research Intelligence Platform — semantic search, citation graphs, "
        "and grounded Q&A over academic literature."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
from app.api.papers import router as papers_router
from app.api.search import router as search_router
from app.api.collections import router as collections_router

app.include_router(papers_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(collections_router, prefix="/api/v1")


# ── Health check ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "papermind",
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to PaperMind API",
        "docs": "/docs",
        "health": "/health",
    }
