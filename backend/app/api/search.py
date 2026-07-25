"""Search and Q&A API routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QueryHistory
from app.db.session import get_db
from app.services.search import semantic_search, get_papers_for_qa
from app.services.groq_llm import ask_question, ask_question_stream, generate_literature_review

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search & Q&A"])


# ── Schemas ──────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    year_min: int | None = None
    year_max: int | None = None


class SearchResult(BaseModel):
    id: int
    title: str
    abstract: str | None
    year: int | None
    venue: str | None
    citation_count: int
    authors: str
    similarity: float
    url: str | None
    is_open_access: bool


class QARequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    top_k: int = Field(default=8, ge=3, le=20, description="Number of papers to use as context")
    stream: bool = Field(default=False, description="Enable SSE streaming")


class QAResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    question: str


class ReviewRequest(BaseModel):
    paper_ids: list[int] = Field(..., min_length=2, max_length=20)
    focus_topic: str | None = Field(default=None, max_length=500)


class ReviewResponse(BaseModel):
    review: str
    paper_count: int


# ── Search endpoint ──────────────────────────────────────────

@router.post("/search", response_model=list[SearchResult])
async def search_papers(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Semantic search over paper abstracts using pgvector cosine similarity.
    Returns papers ranked by relevance to the natural-language query.
    """
    results = await semantic_search(
        query=request.query,
        db=db,
        limit=request.limit,
        year_min=request.year_min,
        year_max=request.year_max,
    )

    if not results:
        return []

    # Log the query
    db.add(QueryHistory(
        query_text=request.query,
        query_type="search",
        results_count=len(results),
    ))

    return [
        SearchResult(
            id=r["id"],
            title=r["title"],
            abstract=r["abstract"],
            year=r["year"],
            venue=r["venue"],
            citation_count=r["citation_count"],
            authors=r["authors"],
            similarity=r["similarity"],
            url=r["url"],
            is_open_access=r.get("is_open_access", False),
        )
        for r in results
    ]


# ── Q&A endpoint ─────────────────────────────────────────────

@router.post("/qa")
async def qa_over_papers(request: QARequest, db: AsyncSession = Depends(get_db)):
    """
    Ask a natural-language question about the indexed papers.
    Uses RAG: retrieves relevant papers via pgvector, then sends
    them as context to Groq LLM for grounded answer generation.
    """
    # Retrieve relevant papers
    paper_contexts = await get_papers_for_qa(
        query=request.question, db=db, top_k=request.top_k
    )

    if not paper_contexts:
        raise HTTPException(
            status_code=404,
            detail="No papers found. Please ingest papers for a topic first.",
        )

    # Log the query
    db.add(QueryHistory(
        query_text=request.question,
        query_type="qa",
        results_count=len(paper_contexts),
    ))
    await db.commit()

    # Streaming response
    if request.stream:
        async def event_generator():
            async for chunk in ask_question_stream(request.question, paper_contexts):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming response
    answer = await ask_question(request.question, paper_contexts)

    return QAResponse(
        answer=answer,
        sources=[
            {"title": p["title"], "year": p["year"], "authors": p["authors"]}
            for p in paper_contexts
        ],
        question=request.question,
    )


# ── Literature review endpoint ───────────────────────────────

@router.post("/review", response_model=ReviewResponse)
async def generate_review(request: ReviewRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a structured literature review from selected papers.
    Select paper IDs from search results, and get an AI-generated
    thematic literature review with citations.
    """
    from app.db.models import Paper, Author, PaperAuthor
    from sqlalchemy import select

    # Fetch selected papers
    result = await db.execute(
        select(Paper).where(Paper.id.in_(request.paper_ids))
    )
    papers = result.scalars().all()

    if len(papers) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 valid papers are required for a literature review.",
        )

    # Build context
    paper_contexts = []
    for paper in papers:
        authors_result = await db.execute(
            select(Author.name)
            .join(PaperAuthor, PaperAuthor.author_id == Author.id)
            .where(PaperAuthor.paper_id == paper.id)
            .order_by(PaperAuthor.position)
        )
        author_names = [a[0] for a in authors_result.fetchall()]

        paper_contexts.append({
            "title": paper.title,
            "abstract": paper.abstract or "No abstract available.",
            "year": paper.year,
            "authors": ", ".join(author_names) if author_names else "Unknown",
            "citation_count": paper.citation_count,
        })

    # Log the query
    db.add(QueryHistory(
        query_text=f"Review: {request.focus_topic or 'general'}",
        query_type="review",
        results_count=len(papers),
    ))

    review = await generate_literature_review(
        paper_contexts=paper_contexts,
        focus_topic=request.focus_topic,
    )

    return ReviewResponse(review=review, paper_count=len(papers))
