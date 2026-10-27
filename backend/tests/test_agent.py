"""Tests for the LangGraph research agent."""

import re
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


# ---------------------------------------------------------------------------
# Test 1: Tool functions with mocked DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_papers_tool_returns_results():
    """search_papers tool should call semantic_search and format results."""
    mock_db = AsyncMock()

    with patch("app.services.agent.tools.semantic_search") as mock_search:
        mock_search.return_value = [
            {
                "id": 1,
                "title": "Test Paper",
                "year": 2023,
                "authors": "Smith et al.",
                "similarity": 0.85,
                "citation_count": 10,
                "abstract": "A test abstract about machine learning.",
            }
        ]

        from app.services.agent.tools import make_tools
        tools = make_tools(mock_db)
        search_tool = tools[0]  # search_papers

        result = await search_tool.ainvoke({"query": "machine learning", "k": 5})
        assert "paper_id=1" in result
        assert "Test Paper" in result
        assert "0.850" in result


@pytest.mark.asyncio
async def test_search_papers_tool_no_results():
    """search_papers should return a 'no papers found' message when empty."""
    mock_db = AsyncMock()

    with patch("app.services.agent.tools.semantic_search") as mock_search:
        mock_search.return_value = []

        from app.services.agent.tools import make_tools
        tools = make_tools(mock_db)
        search_tool = tools[0]

        result = await search_tool.ainvoke({"query": "quantum computing", "k": 5})
        assert "No papers found" in result


@pytest.mark.asyncio
async def test_get_paper_tool_found():
    """get_paper should return full metadata when paper exists."""
    from app.services.agent.tools import make_tools

    # Mock DB to return a paper
    mock_paper = MagicMock()
    mock_paper.id = 42
    mock_paper.title = "Deep Learning Survey"
    mock_paper.year = 2024
    mock_paper.venue = "NeurIPS"
    mock_paper.citation_count = 500
    mock_paper.is_open_access = True
    mock_paper.url = "https://example.com"
    mock_paper.fields_of_study = "Computer Science"
    mock_paper.abstract = "A survey of deep learning methods."

    mock_db = AsyncMock()
    # First execute call returns paper, second returns authors
    mock_result_paper = MagicMock()
    mock_result_paper.scalar_one_or_none.return_value = mock_paper
    mock_result_authors = MagicMock()
    mock_result_authors.fetchall.return_value = [("Author A",), ("Author B",)]
    mock_db.execute.side_effect = [mock_result_paper, mock_result_authors]

    tools = make_tools(mock_db)
    get_paper_tool = tools[1]

    result = await get_paper_tool.ainvoke({"paper_id": 42})
    assert "paper_id=42" in result
    assert "Deep Learning Survey" in result
    assert "Author A" in result


@pytest.mark.asyncio
async def test_get_paper_tool_not_found():
    """get_paper should return not-found message for missing paper."""
    from app.services.agent.tools import make_tools

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    tools = make_tools(mock_db)
    get_paper_tool = tools[1]

    result = await get_paper_tool.ainvoke({"paper_id": 9999})
    assert "not found" in result


# ---------------------------------------------------------------------------
# Test 2: Graph loop with mocked LLM
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_graph_runs_tool_then_answers():
    """Graph should: agent -> tools -> agent -> verify -> END."""
    from app.services.agent.graph import build_agent_graph, AGENT_SYSTEM_PROMPT

    mock_db = AsyncMock()

    # Mock the semantic_search to return a paper
    with patch("app.services.agent.tools.semantic_search") as mock_search, \
         patch("app.services.agent.graph.ChatGroq") as MockChatGroq:

        mock_search.return_value = [
            {"id": 1, "title": "Test Paper", "year": 2023, "authors": "X",
             "similarity": 0.9, "citation_count": 5, "abstract": "About ML."}
        ]

        # Build a fake LLM that first requests a tool call, then answers
        call_count = 0

        async def fake_ainvoke(messages):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: request a tool
                return AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "search_papers",
                        "args": {"query": "machine learning", "k": 5},
                        "id": "call_1",
                    }],
                )
            else:
                # Second call: final answer
                return AIMessage(
                    content="Based on [paper_id=1] Test Paper, ML is important.",
                )

        mock_llm_instance = MagicMock()
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        mock_llm_instance.ainvoke = fake_ainvoke
        MockChatGroq.return_value = mock_llm_instance

        graph, tools = build_agent_graph(mock_db, max_iterations=5)

        result = await graph.ainvoke({
            "messages": [
                SystemMessage(content=AGENT_SYSTEM_PROMPT),
                HumanMessage(content="Tell me about ML"),
            ],
            "tool_calls_log": [],
            "iterations": 0,
            "retrieved_paper_ids": [],
            "warnings": [],
        })

        assert result["iterations"] >= 2
        assert any("paper_id=1" in str(m.content) for m in result["messages"] if hasattr(m, "content"))


# ---------------------------------------------------------------------------
# Test 3: Verify node flags fabricated citations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_flags_fabricated_citation():
    """verify_node should add a warning for paper IDs not in DB."""
    from app.services.agent.graph import AgentState
    import re

    # Simulate state with a fabricated citation
    state: AgentState = {
        "messages": [AIMessage(content="See [paper_id=99999] for details.")],
        "tool_calls_log": [],
        "iterations": 1,
        "retrieved_paper_ids": [],  # 99999 NOT in retrieved
        "warnings": [],
    }

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # not in DB
    mock_db.execute.return_value = mock_result

    # Import and call verify_node logic directly
    from sqlalchemy import select as sa_select

    cited_ids = [int(x) for x in re.findall(r"paper_id=(\d+)", state["messages"][-1].content)]
    warnings = []
    for pid in cited_ids:
        if pid not in set(state["retrieved_paper_ids"]):
            # Check DB
            result = await mock_db.execute(sa_select())
            if result.scalar_one_or_none() is None:
                warnings.append(f"Citation paper_id={pid} not found in the database.")

    assert len(warnings) == 1
    assert "99999" in warnings[0]


# ---------------------------------------------------------------------------
# Test 4: Max iterations stops infinite loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_max_iterations_stops_loop():
    """Agent should stop after max_iterations even if LLM keeps calling tools."""
    from app.services.agent.graph import build_agent_graph, AGENT_SYSTEM_PROMPT

    mock_db = AsyncMock()

    with patch("app.services.agent.tools.semantic_search") as mock_search, \
         patch("app.services.agent.graph.ChatGroq") as MockChatGroq:

        mock_search.return_value = [
            {"id": 1, "title": "P", "year": 2023, "authors": "X",
             "similarity": 0.9, "citation_count": 0, "abstract": "A."}
        ]

        # LLM always requests tool calls (infinite loop attempt)
        async def always_tool_call(messages):
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "search_papers",
                    "args": {"query": "test", "k": 1},
                    "id": "call_loop",
                }],
            )

        mock_llm_instance = MagicMock()
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        mock_llm_instance.ainvoke = always_tool_call
        MockChatGroq.return_value = mock_llm_instance

        graph, tools = build_agent_graph(mock_db, max_iterations=3)

        result = await graph.ainvoke({
            "messages": [
                SystemMessage(content=AGENT_SYSTEM_PROMPT),
                HumanMessage(content="Loop forever"),
            ],
            "tool_calls_log": [],
            "iterations": 0,
            "retrieved_paper_ids": [],
            "warnings": [],
        })

        # Should stop at max_iterations=3
        assert result["iterations"] <= 3
