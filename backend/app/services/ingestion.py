"""Paper ingestion service — orchestrates fetching, storing, and embedding papers."""

import json
import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import (
    Author,
    Citation,
    Paper,
    PaperAuthor,
    PaperEmbedding,
    TopicSearch,
)
from app.services.semantic_scholar import (
    SemanticScholarClient,
    parse_authors,
    parse_paper_data,
)
from app.services.embeddings import embed_texts_batch

logger = logging.getLogger(__name__)


async def ingest_topic(
    topic: str,
    max_papers: int,
    topic_search_id: int,
    db: AsyncSession,
) -> dict:
    """
    Full ingestion pipeline for a topic:
    1. Search Semantic Scholar
    2. Store papers + authors in PostgreSQL
    3. Build citation edges
    4. Embed abstracts into pgvector

    Args:
        topic: Search query string.
        max_papers: Maximum papers to fetch.
        topic_search_id: ID of the TopicSearch record to update.
        db: Async database session.

    Returns:
        Summary dict with counts.
    """
    client = SemanticScholarClient()

    try:
        # Update status to running
        topic_search = await db.get(TopicSearch, topic_search_id)
        if topic_search:
            topic_search.status = "running"
            await db.commit()

        # ── Step 1: Fetch papers from Semantic Scholar ───────
        logger.info(f"Fetching papers for topic: '{topic}'")
        raw_papers = await client.search_papers_bulk(
            query=topic, max_papers=max_papers
        )

        if not raw_papers:
            logger.warning(f"No papers found for topic: '{topic}'")
            if topic_search:
                topic_search.status = "done"
                topic_search.papers_found = 0
                topic_search.completed_at = datetime.utcnow()
                await db.commit()
            return {"papers_found": 0, "papers_stored": 0, "embeddings_created": 0}

        # ── Step 2: Store papers and authors ─────────────────
        papers_stored = 0
        new_paper_ids = []

        for raw in raw_papers:
            if not raw.get("paperId"):
                continue

            paper_data = parse_paper_data(raw)

            # Upsert paper (skip if already exists)
            existing = await db.execute(
                select(Paper).where(
                    Paper.semantic_scholar_id == paper_data["semantic_scholar_id"]
                )
            )
            existing_paper = existing.scalar_one_or_none()

            if existing_paper:
                # Update citation counts (they change over time)
                existing_paper.citation_count = paper_data["citation_count"]
                existing_paper.reference_count = paper_data["reference_count"]
                continue

            paper = Paper(**paper_data)
            db.add(paper)
            await db.flush()  # Get the paper.id

            # Store authors
            for i, author_data in enumerate(parse_authors(raw)):
                # Upsert author
                existing_author = None
                if author_data["semantic_scholar_id"]:
                    result = await db.execute(
                        select(Author).where(
                            Author.semantic_scholar_id
                            == author_data["semantic_scholar_id"]
                        )
                    )
                    existing_author = result.scalar_one_or_none()

                if not existing_author:
                    author = Author(**author_data)
                    db.add(author)
                    await db.flush()
                    author_id = author.id
                else:
                    author_id = existing_author.id

                # Link paper ↔ author
                pa = PaperAuthor(
                    paper_id=paper.id, author_id=author_id, position=i
                )
                db.add(pa)

            new_paper_ids.append(paper.id)
            papers_stored += 1

        await db.commit()
        logger.info(f"Stored {papers_stored} new papers for topic: '{topic}'")

        # ── Step 3: Build citation edges ─────────────────────
        citations_created = await _build_citation_edges(raw_papers, db)

        # ── Step 4: Embed abstracts ──────────────────────────
        embeddings_created = await _embed_papers(new_paper_ids, db)

        # Update topic search record
        if topic_search:
            topic_search.status = "done"
            topic_search.papers_found = len(raw_papers)
            topic_search.papers_embedded = embeddings_created
            topic_search.completed_at = datetime.utcnow()
            await db.commit()

        return {
            "papers_found": len(raw_papers),
            "papers_stored": papers_stored,
            "citations_created": citations_created,
            "embeddings_created": embeddings_created,
        }

    except Exception as e:
        logger.error(f"Ingestion failed for topic '{topic}': {e}")
        if topic_search:
            topic_search.status = "failed"
            await db.commit()
        raise

    finally:
        await client.close()


async def _build_citation_edges(
    raw_papers: list[dict], db: AsyncSession
) -> int:
    """
    Build citation graph edges from reference data in API responses.
    Only creates edges between papers that exist in our database.
    """
    count = 0
    # Collect all known S2 IDs for fast lookup
    all_s2_ids = {p["paperId"] for p in raw_papers if p.get("paperId")}

    for raw in raw_papers:
        citing_s2_id = raw.get("paperId")
        if not citing_s2_id:
            continue

        # Get references (papers this paper cites)
        references = raw.get("references") or []
        for ref in references:
            cited_s2_id = ref.get("paperId") if isinstance(ref, dict) else None
            if not cited_s2_id or cited_s2_id not in all_s2_ids:
                continue

            # Look up both paper IDs in our database
            citing_result = await db.execute(
                select(Paper.id).where(Paper.semantic_scholar_id == citing_s2_id)
            )
            cited_result = await db.execute(
                select(Paper.id).where(Paper.semantic_scholar_id == cited_s2_id)
            )

            citing_id = citing_result.scalar_one_or_none()
            cited_id = cited_result.scalar_one_or_none()

            if citing_id and cited_id:
                # Upsert citation edge
                existing = await db.execute(
                    select(Citation).where(
                        Citation.citing_paper_id == citing_id,
                        Citation.cited_paper_id == cited_id,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(
                        Citation(
                            citing_paper_id=citing_id, cited_paper_id=cited_id
                        )
                    )
                    count += 1

    await db.commit()
    logger.info(f"Created {count} citation edges.")
    return count


async def _embed_papers(paper_ids: list[int], db: AsyncSession) -> int:
    """
    Embed abstracts for papers that don't already have embeddings.
    Uses batch embedding for efficiency.
    """
    if not paper_ids:
        return 0

    # Fetch papers without embeddings
    result = await db.execute(
        select(Paper).where(
            Paper.id.in_(paper_ids),
            Paper.abstract.isnot(None),
            Paper.abstract != "",
        )
    )
    papers = result.scalars().all()

    # Filter out papers that already have embeddings
    papers_to_embed = []
    for paper in papers:
        existing = await db.execute(
            select(PaperEmbedding).where(PaperEmbedding.paper_id == paper.id)
        )
        if not existing.scalar_one_or_none():
            papers_to_embed.append(paper)

    if not papers_to_embed:
        return 0

    # Batch embed
    texts = [
        f"{p.title}. {p.abstract}" for p in papers_to_embed
    ]
    embeddings = embed_texts_batch(texts)

    # Store embeddings
    for paper, embedding in zip(papers_to_embed, embeddings):
        db.add(PaperEmbedding(paper_id=paper.id, embedding=embedding))

    await db.commit()
    logger.info(f"Embedded {len(papers_to_embed)} paper abstracts.")
    return len(papers_to_embed)
