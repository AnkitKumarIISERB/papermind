"""Search service — semantic search over paper embeddings via pgvector."""

import logging
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Paper, PaperEmbedding, Author, PaperAuthor
from app.services.embeddings import embed_text

logger = logging.getLogger(__name__)


async def semantic_search(
    query: str,
    db: AsyncSession,
    limit: int = 10,
    year_min: int | None = None,
    year_max: int | None = None,
) -> list[dict[str, Any]]:
    """
    Perform semantic search over paper abstracts using pgvector cosine similarity.

    Args:
        query: Natural-language search query.
        db: Async database session.
        limit: Maximum number of results.
        year_min: Optional minimum publication year filter.
        year_max: Optional maximum publication year filter.

    Returns:
        List of paper dicts ranked by semantic similarity, with scores.
    """
    # Embed the query
    query_embedding = embed_text(query)

    # Build the pgvector cosine distance query
    # cosine_distance = 1 - cosine_similarity, so lower is better
    embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

    # Build WHERE clauses
    where_clauses = ["p.abstract IS NOT NULL"]
    params = {"limit": limit}

    if year_min is not None:
        where_clauses.append("p.year >= :year_min")
        params["year_min"] = year_min
    if year_max is not None:
        where_clauses.append("p.year <= :year_max")
        params["year_max"] = year_max

    where_sql = " AND ".join(where_clauses)

    sql = text(f"""
        SELECT
            p.id,
            p.semantic_scholar_id,
            p.title,
            p.abstract,
            p.year,
            p.venue,
            p.citation_count,
            p.url,
            p.is_open_access,
            p.fields_of_study,
            1 - (pe.embedding <=> '{embedding_str}'::vector) AS similarity
        FROM papers p
        JOIN paper_embeddings pe ON pe.paper_id = p.id
        WHERE {where_sql}
        ORDER BY pe.embedding <=> '{embedding_str}'::vector
        LIMIT :limit
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    papers = []
    for row in rows:
        # Fetch authors for this paper
        authors_result = await db.execute(
            select(Author.name)
            .join(PaperAuthor, PaperAuthor.author_id == Author.id)
            .where(PaperAuthor.paper_id == row.id)
            .order_by(PaperAuthor.position)
        )
        author_names = [a[0] for a in authors_result.fetchall()]

        papers.append({
            "id": row.id,
            "semantic_scholar_id": row.semantic_scholar_id,
            "title": row.title,
            "abstract": row.abstract,
            "year": row.year,
            "venue": row.venue,
            "citation_count": row.citation_count,
            "url": row.url,
            "is_open_access": row.is_open_access,
            "fields_of_study": row.fields_of_study,
            "authors": ", ".join(author_names) if author_names else "Unknown",
            "similarity": round(float(row.similarity), 4),
        })

    return papers


async def get_papers_for_qa(
    query: str,
    db: AsyncSession,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """
    Retrieve top-k most relevant papers for RAG Q&A context.
    Returns only the fields needed for the LLM prompt.
    """
    results = await semantic_search(query=query, db=db, limit=top_k)
    return [
        {
            "title": r["title"],
            "abstract": r["abstract"],
            "year": r["year"],
            "authors": r["authors"],
            "citation_count": r["citation_count"],
        }
        for r in results
        if r.get("abstract")
    ]
