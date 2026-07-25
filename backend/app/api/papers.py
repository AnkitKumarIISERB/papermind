"""Paper discovery and ingestion API routes."""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Author,
    Citation,
    Collection,
    CollectionPaper,
    Paper,
    PaperAuthor,
    PaperEmbedding,
    TopicSearch,
)
from app.db.session import get_db
from app.core.celery_app import ingest_topic_task
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["Papers"])
settings = get_settings()


# ── Request / Response schemas ───────────────────────────────

class TopicSearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500, description="Research topic to search")
    max_papers: int = Field(default=200, ge=10, le=500, description="Max papers to fetch")
    year_range: str | None = Field(default=None, description="Year filter, e.g. '2020-2024'")


class TopicSearchResponse(BaseModel):
    id: int
    topic: str
    status: str
    celery_task_id: str | None
    papers_found: int = 0
    papers_embedded: int = 0


class PaperResponse(BaseModel):
    id: int
    semantic_scholar_id: str
    title: str
    abstract: str | None
    year: int | None
    venue: str | None
    citation_count: int
    url: str | None
    is_open_access: bool
    fields_of_study: list[str] | None
    authors: list[str]
    has_embedding: bool


class PaperDetailResponse(PaperResponse):
    references: list[dict[str, Any]]
    citations: list[dict[str, Any]]


class GraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class StatsResponse(BaseModel):
    total_papers: int
    total_authors: int
    total_citations: int
    total_embeddings: int
    year_distribution: dict[str, int]
    top_authors: list[dict[str, Any]]


# ── Endpoints ────────────────────────────────────────────────

@router.post("/ingest", response_model=TopicSearchResponse, status_code=202)
async def ingest_topic(request: TopicSearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingest papers for a research topic.
    Runs synchronously in-process (no Celery worker needed).
    """
    from app.services.ingestion import ingest_topic as run_ingestion

    # Create topic search record
    topic_search = TopicSearch(
        topic=request.topic,
        status="running",
    )
    db.add(topic_search)
    await db.commit()
    await db.refresh(topic_search)

    try:
        result = await run_ingestion(
            topic=request.topic,
            max_papers=request.max_papers,
            topic_search_id=topic_search.id,
            db=db,
        )
        logger.info(f"Ingestion complete: {result}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        topic_search.status = "failed"
        await db.commit()

    # Refresh to get updated status from ingestion service
    await db.refresh(topic_search)

    return TopicSearchResponse(
        id=topic_search.id,
        topic=request.topic,
        status=topic_search.status,
        celery_task_id=None,
        papers_found=topic_search.papers_found or 0,
        papers_embedded=topic_search.papers_embedded or 0,
    )


@router.get("/ingest/{search_id}/status")
async def get_ingestion_status(search_id: int, db: AsyncSession = Depends(get_db)):
    """Poll the status of a paper ingestion job."""
    topic_search = await db.get(TopicSearch, search_id)
    if not topic_search:
        raise HTTPException(status_code=404, detail="Topic search not found")

    return {
        "id": topic_search.id,
        "topic": topic_search.topic,
        "status": topic_search.status,
        "papers_found": topic_search.papers_found,
        "papers_embedded": topic_search.papers_embedded,
        "created_at": topic_search.created_at.isoformat() if topic_search.created_at else None,
        "completed_at": topic_search.completed_at.isoformat() if topic_search.completed_at else None,
    }


@router.get("/", response_model=list[PaperResponse])
async def list_papers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="citation_count", enum=["citation_count", "year", "title"]),
    order: str = Query(default="desc", enum=["asc", "desc"]),
    db: AsyncSession = Depends(get_db),
):
    """List all indexed papers with pagination and sorting."""
    sort_column = getattr(Paper, sort_by, Paper.citation_count)
    order_func = sort_column.desc() if order == "desc" else sort_column.asc()

    result = await db.execute(
        select(Paper).order_by(order_func).offset(offset).limit(limit)
    )
    papers = result.scalars().all()

    response = []
    for paper in papers:
        authors = await _get_paper_authors(paper.id, db)
        has_embedding = await _has_embedding(paper.id, db)
        fields = json.loads(paper.fields_of_study) if paper.fields_of_study else None

        response.append(PaperResponse(
            id=paper.id,
            semantic_scholar_id=paper.semantic_scholar_id,
            title=paper.title,
            abstract=paper.abstract,
            year=paper.year,
            venue=paper.venue,
            citation_count=paper.citation_count,
            url=paper.url,
            is_open_access=paper.is_open_access,
            fields_of_study=fields,
            authors=authors,
            has_embedding=has_embedding,
        ))

    return response


@router.get("/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed info for a single paper, including its citation graph neighbors."""
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    authors = await _get_paper_authors(paper.id, db)
    has_embedding = await _has_embedding(paper.id, db)
    fields = json.loads(paper.fields_of_study) if paper.fields_of_study else None

    # Get references (papers this paper cites)
    refs_result = await db.execute(
        select(Paper.id, Paper.title, Paper.year, Paper.citation_count)
        .join(Citation, Citation.cited_paper_id == Paper.id)
        .where(Citation.citing_paper_id == paper.id)
    )
    references = [
        {"id": r.id, "title": r.title, "year": r.year, "citation_count": r.citation_count}
        for r in refs_result.fetchall()
    ]

    # Get citations (papers that cite this paper)
    cites_result = await db.execute(
        select(Paper.id, Paper.title, Paper.year, Paper.citation_count)
        .join(Citation, Citation.citing_paper_id == Paper.id)
        .where(Citation.cited_paper_id == paper.id)
    )
    citations = [
        {"id": r.id, "title": r.title, "year": r.year, "citation_count": r.citation_count}
        for r in cites_result.fetchall()
    ]

    return PaperDetailResponse(
        id=paper.id,
        semantic_scholar_id=paper.semantic_scholar_id,
        title=paper.title,
        abstract=paper.abstract,
        year=paper.year,
        venue=paper.venue,
        citation_count=paper.citation_count,
        url=paper.url,
        is_open_access=paper.is_open_access,
        fields_of_study=fields,
        authors=authors,
        has_embedding=has_embedding,
        references=references,
        citations=citations,
    )


@router.get("/graph/citation", response_model=GraphResponse)
async def get_citation_graph(
    min_citations: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=10, le=500),
    similarity_threshold: float = Query(default=0.55, ge=0.3, le=0.95),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the knowledge graph with similarity-based edges.
    Papers are connected when their embedding cosine similarity exceeds the threshold.
    This creates meaningful topic clusters in the visualization.
    """
    # Get top papers by citation count
    papers_result = await db.execute(
        select(Paper)
        .where(Paper.citation_count >= min_citations)
        .order_by(Paper.citation_count.desc())
        .limit(limit)
    )
    papers = papers_result.scalars().all()
    paper_ids = [p.id for p in papers]
    paper_id_set = set(paper_ids)

    # Build nodes
    nodes = []
    for paper in papers:
        authors = await _get_paper_authors(paper.id, db)
        nodes.append({
            "id": paper.id,
            "label": _truncate(paper.title, 60),
            "title": paper.title,
            "year": paper.year,
            "citationCount": paper.citation_count,
            "authors": ", ".join(authors[:3]) + ("..." if len(authors) > 3 else ""),
            "url": paper.url,
            "venue": paper.venue,
        })

    # Build similarity-based edges using pgvector cosine distance
    edges = []
    if len(paper_ids) > 1:
        similarity_query = text("""
            SELECT
                e1.paper_id AS paper_a,
                e2.paper_id AS paper_b,
                1 - (e1.embedding <=> e2.embedding) AS similarity
            FROM paper_embeddings e1
            CROSS JOIN paper_embeddings e2
            WHERE e1.paper_id < e2.paper_id
              AND e1.paper_id = ANY(:paper_ids)
              AND e2.paper_id = ANY(:paper_ids)
              AND 1 - (e1.embedding <=> e2.embedding) > :threshold
            ORDER BY similarity DESC
            LIMIT 500
        """)

        try:
            edge_result = await db.execute(
                similarity_query,
                {"paper_ids": paper_ids, "threshold": similarity_threshold}
            )
            for row in edge_result.fetchall():
                edges.append({
                    "from": row[0],
                    "to": row[1],
                    "similarity": round(float(row[2]), 3),
                })
        except Exception as e:
            logger.warning(f"Similarity edge query failed: {e}")
            # Fallback to citation edges
            edges_result = await db.execute(
                select(Citation).where(
                    Citation.citing_paper_id.in_(paper_id_set),
                    Citation.cited_paper_id.in_(paper_id_set),
                )
            )
            edges = [
                {"from": edge.citing_paper_id, "to": edge.cited_paper_id}
                for edge in edges_result.scalars().all()
            ]

    return GraphResponse(nodes=nodes, edges=edges)


@router.get("/stats/overview", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate statistics about the indexed paper collection."""
    total_papers = (await db.execute(select(func.count(Paper.id)))).scalar() or 0
    total_authors = (await db.execute(select(func.count(Author.id)))).scalar() or 0
    total_citations = (await db.execute(select(func.count(Citation.id)))).scalar() or 0
    total_embeddings = (await db.execute(select(func.count(PaperEmbedding.id)))).scalar() or 0

    # Year distribution
    year_result = await db.execute(
        select(Paper.year, func.count(Paper.id))
        .where(Paper.year.isnot(None))
        .group_by(Paper.year)
        .order_by(Paper.year)
    )
    year_distribution = {str(row[0]): row[1] for row in year_result.fetchall()}

    # Top authors by paper count
    top_authors_result = await db.execute(
        select(Author.name, func.count(PaperAuthor.paper_id).label("count"))
        .join(PaperAuthor, PaperAuthor.author_id == Author.id)
        .group_by(Author.id, Author.name)
        .order_by(text("count DESC"))
        .limit(15)
    )
    top_authors = [
        {"name": row[0], "paper_count": row[1]}
        for row in top_authors_result.fetchall()
    ]

    return StatsResponse(
        total_papers=total_papers,
        total_authors=total_authors,
        total_citations=total_citations,
        total_embeddings=total_embeddings,
        year_distribution=year_distribution,
        top_authors=top_authors,
    )


# ── Helpers ──────────────────────────────────────────────────

async def _get_paper_authors(paper_id: int, db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Author.name)
        .join(PaperAuthor, PaperAuthor.author_id == Author.id)
        .where(PaperAuthor.paper_id == paper_id)
        .order_by(PaperAuthor.position)
    )
    return [row[0] for row in result.fetchall()]


async def _has_embedding(paper_id: int, db: AsyncSession) -> bool:
    result = await db.execute(
        select(PaperEmbedding.id).where(PaperEmbedding.paper_id == paper_id)
    )
    return result.scalar_one_or_none() is not None


def _truncate(text: str, max_len: int) -> str:
    if not text:
        return ""
    return text[:max_len] + "..." if len(text) > max_len else text
