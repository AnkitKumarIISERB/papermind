"""Tests for service layer logic."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.semantic_scholar import parse_paper_data, parse_authors
from app.services.groq_llm import _format_paper_contexts


# ── Semantic Scholar Parser Tests ────────────────────────────

class TestParsePaperData:
    def test_basic_parsing(self):
        raw = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": "This is a test abstract.",
            "year": 2024,
            "venue": "NeurIPS",
            "citationCount": 42,
            "referenceCount": 10,
            "influentialCitationCount": 5,
            "url": "https://example.com/paper",
            "isOpenAccess": True,
            "fieldsOfStudy": ["Computer Science", "Medicine"],
        }
        result = parse_paper_data(raw)

        assert result["semantic_scholar_id"] == "abc123"
        assert result["title"] == "Test Paper"
        assert result["abstract"] == "This is a test abstract."
        assert result["year"] == 2024
        assert result["venue"] == "NeurIPS"
        assert result["citation_count"] == 42
        assert result["is_open_access"] is True
        assert '"Computer Science"' in result["fields_of_study"]

    def test_missing_optional_fields(self):
        raw = {
            "paperId": "xyz789",
            "title": "Minimal Paper",
        }
        result = parse_paper_data(raw)

        assert result["semantic_scholar_id"] == "xyz789"
        assert result["title"] == "Minimal Paper"
        assert result["abstract"] is None
        assert result["year"] is None
        assert result["citation_count"] == 0
        assert result["is_open_access"] is False
        assert result["fields_of_study"] is None

    def test_null_citation_count(self):
        raw = {
            "paperId": "test1",
            "title": "Paper",
            "citationCount": None,
        }
        result = parse_paper_data(raw)
        assert result["citation_count"] == 0


class TestParseAuthors:
    def test_basic_authors(self):
        raw = {
            "authors": [
                {"authorId": "auth1", "name": "Alice Smith"},
                {"authorId": "auth2", "name": "Bob Jones"},
            ]
        }
        result = parse_authors(raw)

        assert len(result) == 2
        assert result[0]["name"] == "Alice Smith"
        assert result[0]["semantic_scholar_id"] == "auth1"
        assert result[1]["name"] == "Bob Jones"

    def test_no_authors(self):
        raw = {"authors": None}
        result = parse_authors(raw)
        assert result == []

    def test_missing_author_id(self):
        raw = {
            "authors": [{"name": "Unknown Author"}]
        }
        result = parse_authors(raw)
        assert len(result) == 1
        assert result[0]["semantic_scholar_id"] is None
        assert result[0]["name"] == "Unknown Author"


# ── Groq Context Formatting Tests ────────────────────────────

class TestFormatPaperContexts:
    def test_single_paper(self):
        papers = [{
            "title": "Test Paper",
            "abstract": "Test abstract.",
            "year": 2024,
            "authors": "Alice, Bob",
            "citation_count": 10,
        }]
        result = _format_paper_contexts(papers)

        assert "Test Paper" in result
        assert "Test abstract." in result
        assert "2024" in result
        assert "Alice, Bob" in result
        assert "[Paper 1]" in result

    def test_multiple_papers(self):
        papers = [
            {"title": f"Paper {i}", "abstract": f"Abstract {i}", "year": 2020 + i, "authors": f"Author {i}", "citation_count": i}
            for i in range(3)
        ]
        result = _format_paper_contexts(papers)

        assert "[Paper 1]" in result
        assert "[Paper 2]" in result
        assert "[Paper 3]" in result
        assert "---" in result  # Separator

    def test_empty_list(self):
        result = _format_paper_contexts([])
        assert result == ""

    def test_missing_fields(self):
        papers = [{"title": "Only Title"}]
        result = _format_paper_contexts(papers)
        assert "Only Title" in result
        assert "Unknown authors" in result
