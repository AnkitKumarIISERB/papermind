"""LangChain tools that wrap existing PaperMind services.

Each tool is async-safe and reuses existing DB queries / services.
They accept a db session injected at graph-construction time.
"""

import logging
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Paper, PaperEmbedding, Author, PaperAuthor
from app.services.embeddings import embed_text
from app.services.search import semantic_search, get_papers_for_qa
from app.services.groq_llm import generate_literature_review

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tools are closures over a db session, created via make_tools(db).
# This avoids global state and keeps each agent invocation isolated.
# ---------------------------------------------------------------------------


def make_tools(db: AsyncSession):
    """Return a list of LangChain tool instances bound to *db*."""

    @tool
    async def search_papers(query: str, k: int = 5) -> str:
        """Search the paper database by semantic similarity.
        Returns the top-k most relevant papers for a natural-language query.
        Use this tool to find papers related to a topic, method, or concept."""
        results = await semantic_search(query=query, db=db, limit=k)
        if not results:
            return "No papers found for this query."
        lines = []
        for r in results:
            lines.append(
                f"- [paper_id={r['id']}] \"{r['title']}\" "
                f"({r.get('year', 'n.d.')}) by {r.get('authors', 'Unknown')} "
                f"— similarity={r['similarity']:.3f}, "
                f"citations={r.get('citation_count', 0)}"
            )
            # Include abstract snippet (first 200 chars)
            abstract = r.get("abstract") or ""
            if abstract:
                lines.append(f"  Abstract: {abstract[:200]}...")
        return "\n".join(lines)

    @tool
    async def get_paper(paper_id: int) -> str:
        """Get full stored metadata and abstract for a specific paper by its ID.
        Use this after search_papers to get detailed information."""
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        if paper is None:
            return f"Paper with id={paper_id} not found in the database."

        # Fetch authors
        authors_result = await db.execute(
            select(Author.name)
            .join(PaperAuthor, PaperAuthor.author_id == Author.id)
            .where(PaperAuthor.paper_id == paper.id)
            .order_by(PaperAuthor.position)
        )
        author_names = [a[0] for a in authors_result.fetchall()]

        return (
            f"[paper_id={paper.id}]\n"
            f"Title: {paper.title}\n"
            f"Authors: {', '.join(author_names) if author_names else 'Unknown'}\n"
            f"Year: {paper.year}\n"
            f"Venue: {paper.venue or 'N/A'}\n"
            f"Citations: {paper.citation_count}\n"
            f"Open Access: {paper.is_open_access}\n"
            f"URL: {paper.url or 'N/A'}\n"
            f"Fields: {paper.fields_of_study or 'N/A'}\n"
            f"Abstract: {paper.abstract or 'No abstract available.'}"
        )

    @tool
    async def find_similar_papers(paper_id: int, k: int = 5) -> str:
        """Find papers similar to a given paper (by paper_id) using pgvector cosine similarity.
        Use this to explore related work around a specific paper."""
        # Get the embedding for the source paper
        result = await db.execute(
            select(PaperEmbedding.embedding).where(
                PaperEmbedding.paper_id == paper_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return f"Paper id={paper_id} has no embedding. Cannot find similar papers."

        embedding_str = f"[{','.join(str(x) for x in row)}]"

        sql = text(f"""
            SELECT
                p.id, p.title, p.year, p.citation_count,
                1 - (pe.embedding <=> '{embedding_str}'::vector) AS similarity
            FROM papers p
            JOIN paper_embeddings pe ON pe.paper_id = p.id
            WHERE p.id != :source_id AND p.abstract IS NOT NULL
            ORDER BY pe.embedding <=> '{embedding_str}'::vector
            LIMIT :k
        """)
        result = await db.execute(sql, {"source_id": paper_id, "k": k})
        rows = result.fetchall()

        if not rows:
            return "No similar papers found."

        lines = []
        for r in rows:
            lines.append(
                f"- [paper_id={r.id}] \"{r.title}\" ({r.year or 'n.d.'}) "
                f"— similarity={float(r.similarity):.3f}, citations={r.citation_count}"
            )
        return "\n".join(lines)

    @tool
    async def generate_review(topic: str) -> str:
        """Generate a structured literature review on a topic using papers from the database.
        Retrieves relevant papers and produces a thematic review with citations."""
        paper_contexts = await get_papers_for_qa(query=topic, db=db, top_k=8)
        if not paper_contexts:
            return "No papers found for this topic. Cannot generate a review."

        review = await generate_literature_review(
            paper_contexts=paper_contexts,
            focus_topic=topic,
        )
        return review

    return [search_papers, get_paper, find_similar_papers, generate_review]
