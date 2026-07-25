"""Async client for the Semantic Scholar Academic Graph API."""

import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SemanticScholarClient:
    """Fetches papers, authors, and citation data from Semantic Scholar."""

    BASE_URL = settings.semantic_scholar_base_url
    PAPER_FIELDS = (
        "paperId,title,abstract,year,venue,citationCount,referenceCount,"
        "influentialCitationCount,isOpenAccess,url,fieldsOfStudy,"
        "authors,references,citations"
    )
    SEARCH_FIELDS = (
        "paperId,title,abstract,year,venue,citationCount,referenceCount,"
        "influentialCitationCount,isOpenAccess,url,fieldsOfStudy,authors"
    )

    def __init__(self) -> None:
        headers = {"Accept": "application/json"}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ── Topic search ─────────────────────────────────────────
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
        year_range: str | None = None,
    ) -> dict[str, Any]:
        """
        Search for papers by topic query.

        Args:
            query: Search string (e.g. "multimodal depression detection")
            limit: Max results per page (API max is 100)
            offset: Pagination offset
            year_range: Optional year filter (e.g. "2020-2024")

        Returns:
            API response dict with 'total' and 'data' keys.
        """
        params: dict[str, Any] = {
            "query": query,
            "limit": min(limit, 100),
            "offset": offset,
            "fields": self.SEARCH_FIELDS,
        }
        if year_range:
            params["year"] = year_range

        resp = await self._client.get("/paper/search", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_papers_bulk(
        self,
        query: str,
        max_papers: int = 500,
        year_range: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch up to max_papers by paginating through search results.
        Respects rate limits with small delays between pages.
        """
        all_papers: list[dict[str, Any]] = []
        offset = 0
        page_size = 100

        while offset < max_papers:
            try:
                result = await self.search_papers(
                    query=query,
                    limit=min(page_size, max_papers - offset),
                    offset=offset,
                    year_range=year_range,
                )
                papers = result.get("data", [])
                if not papers:
                    break

                all_papers.extend(papers)
                offset += len(papers)

                total = result.get("total", 0)
                if offset >= total:
                    break

                # Rate limiting — be polite to the API
                await asyncio.sleep(0.2)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("Rate limited by Semantic Scholar, waiting 5s...")
                    await asyncio.sleep(5)
                    continue
                raise

        logger.info(f"Fetched {len(all_papers)} papers for query: '{query}'")
        return all_papers

    # ── Single paper detail ──────────────────────────────────
    async def get_paper(self, paper_id: str) -> dict[str, Any]:
        """
        Fetch detailed metadata for a single paper, including
        references and citations (for building the citation graph).
        """
        params = {"fields": self.PAPER_FIELDS}
        resp = await self._client.get(f"/paper/{paper_id}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_paper_references(
        self, paper_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch papers that this paper references."""
        params = {
            "fields": "paperId,title,year,citationCount",
            "limit": limit,
        }
        resp = await self._client.get(
            f"/paper/{paper_id}/references", params=params
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        # Each entry has a "citedPaper" key
        return [
            entry["citedPaper"]
            for entry in data
            if entry.get("citedPaper", {}).get("paperId")
        ]

    async def get_paper_citations(
        self, paper_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch papers that cite this paper."""
        params = {
            "fields": "paperId,title,year,citationCount",
            "limit": limit,
        }
        resp = await self._client.get(
            f"/paper/{paper_id}/citations", params=params
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        # Each entry has a "citingPaper" key
        return [
            entry["citingPaper"]
            for entry in data
            if entry.get("citingPaper", {}).get("paperId")
        ]

    # ── Batch paper details (for building citation graph) ────
    async def get_papers_batch(
        self, paper_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Fetch details for multiple papers in a single POST request.
        Semantic Scholar batch endpoint supports up to 500 IDs.
        """
        if not paper_ids:
            return []

        # Batch endpoint
        resp = await self._client.post(
            "/paper/batch",
            params={"fields": self.SEARCH_FIELDS},
            json={"ids": paper_ids[:500]},
        )
        resp.raise_for_status()
        results = resp.json()
        # Filter out None entries (papers not found)
        return [p for p in results if p is not None]


def parse_paper_data(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert raw Semantic Scholar API response into a dict
    matching our Paper model fields.
    """
    fields_of_study = raw.get("fieldsOfStudy") or []

    return {
        "semantic_scholar_id": raw["paperId"],
        "title": raw.get("title", "Untitled"),
        "abstract": raw.get("abstract"),
        "year": raw.get("year"),
        "venue": raw.get("venue"),
        "citation_count": raw.get("citationCount", 0) or 0,
        "reference_count": raw.get("referenceCount", 0) or 0,
        "influential_citation_count": raw.get("influentialCitationCount", 0) or 0,
        "url": raw.get("url"),
        "is_open_access": raw.get("isOpenAccess", False),
        "fields_of_study": json.dumps(fields_of_study) if fields_of_study else None,
    }


def parse_authors(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract author list from a Semantic Scholar paper response."""
    authors_raw = raw.get("authors") or []
    return [
        {
            "semantic_scholar_id": a.get("authorId"),
            "name": a.get("name", "Unknown"),
        }
        for a in authors_raw
    ]
