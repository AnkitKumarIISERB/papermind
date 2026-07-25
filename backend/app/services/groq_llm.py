"""Groq LLM service for RAG Q&A and literature review generation."""

import logging
from typing import AsyncGenerator

from groq import AsyncGroq

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_groq_client() -> AsyncGroq:
    """Create an async Groq client."""
    return AsyncGroq(api_key=settings.groq_api_key)


# ── System prompts ───────────────────────────────────────────

QA_SYSTEM_PROMPT = """You are PaperMind, an AI research assistant. You answer questions about academic literature using ONLY the paper abstracts provided below as context.

RULES:
1. Answer ONLY from the provided paper abstracts. Do NOT use your training knowledge.
2. If the answer cannot be found in the provided abstracts, say "I cannot find information about this in the current paper collection."
3. Always cite papers by [Author et al., Year] or [Title, Year] format.
4. Be specific — reference exact methods, datasets, or findings mentioned in the abstracts.
5. Structure your answers clearly with bullet points or numbered lists when comparing multiple papers.
6. Keep answers concise but thorough.

CONTEXT (Paper Abstracts):
{context}
"""

REVIEW_SYSTEM_PROMPT = """You are PaperMind, an AI research assistant. Generate a structured literature review section from the provided paper abstracts.

RULES:
1. Use ONLY the provided paper abstracts. Do NOT add information from your training knowledge.
2. Group papers thematically — identify common approaches, methods, or findings.
3. Compare and contrast methods across papers.
4. Identify research gaps or open questions.
5. Use proper academic citation format: [Author et al., Year].
6. Write in formal academic English suitable for a research paper.
7. Structure the review with clear subsection headings.

PAPERS:
{context}
"""


# ── Q&A ──────────────────────────────────────────────────────

async def ask_question(
    question: str,
    paper_contexts: list[dict],
) -> str:
    """
    Answer a research question grounded in retrieved paper abstracts.

    Args:
        question: User's natural-language question.
        paper_contexts: List of dicts with 'title', 'abstract', 'year', 'authors'.

    Returns:
        LLM-generated answer grounded in the provided papers.
    """
    context = _format_paper_contexts(paper_contexts)
    system_prompt = QA_SYSTEM_PROMPT.format(context=context)

    client = get_groq_client()
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        max_tokens=2048,
    )

    return response.choices[0].message.content


async def ask_question_stream(
    question: str,
    paper_contexts: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Stream a research Q&A answer via SSE.

    Yields:
        Chunks of the LLM response as they are generated.
    """
    context = _format_paper_contexts(paper_contexts)
    system_prompt = QA_SYSTEM_PROMPT.format(context=context)

    client = get_groq_client()
    stream = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
        max_tokens=2048,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ── Literature review ────────────────────────────────────────

async def generate_literature_review(
    paper_contexts: list[dict],
    focus_topic: str | None = None,
) -> str:
    """
    Generate a structured literature review from selected papers.

    Args:
        paper_contexts: List of paper dicts to include in the review.
        focus_topic: Optional topic to focus the review on.

    Returns:
        Markdown-formatted literature review section.
    """
    context = _format_paper_contexts(paper_contexts)
    system_prompt = REVIEW_SYSTEM_PROMPT.format(context=context)

    user_msg = "Generate a comprehensive literature review from the papers above."
    if focus_topic:
        user_msg += f" Focus specifically on: {focus_topic}"

    client = get_groq_client()
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    return response.choices[0].message.content


# ── Helpers ──────────────────────────────────────────────────

def _format_paper_contexts(papers: list[dict]) -> str:
    """Format paper metadata + abstracts into a single context string."""
    parts = []
    for i, p in enumerate(papers, 1):
        authors = p.get("authors", "Unknown authors")
        year = p.get("year", "n.d.")
        title = p.get("title", "Untitled")
        abstract = p.get("abstract", "No abstract available.")
        citations = p.get("citation_count", 0)

        parts.append(
            f"[Paper {i}]\n"
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Year: {year}\n"
            f"Citations: {citations}\n"
            f"Abstract: {abstract}\n"
        )

    return "\n---\n".join(parts)
