"""LangGraph StateGraph for the research agent.

Flow:  agent -> [tools -> agent]* -> verify -> END
- agent: ChatGroq with bound tools decides whether to call tools or answer
- tools: ToolNode executes tool calls
- verify: checks that cited paper IDs exist in the DB
"""

import logging
import re
import time
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Paper
from app.services.agent.tools import make_tools

logger = logging.getLogger(__name__)
settings = get_settings()

# ── System prompt ─────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """You are PaperMind Agent, an AI research assistant with access to a database of academic papers.

RULES:
1. Answer ONLY from tool results. Do NOT use your training knowledge to make claims about papers.
2. Always cite papers by their paper_id (e.g., [paper_id=42]) so citations can be verified.
3. When retrieval returns no results, say "I could not find information about this in the current paper collection."
4. NEVER invent or hallucinate paper titles, authors, or findings.
5. Use search_papers first to find relevant papers, then get_paper for details if needed.
6. Use find_similar_papers to explore related work around a specific paper.
7. Use generate_review only when explicitly asked for a literature review.
8. Be concise but thorough. Structure answers with bullet points when comparing papers.
"""


# ── State schema ──────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_calls_log: list[dict[str, Any]]
    iterations: int
    retrieved_paper_ids: list[int]
    warnings: list[str]


# ── Graph builder ─────────────────────────────────────────────

def build_agent_graph(db: AsyncSession, max_iterations: int | None = None):
    """Build and compile the LangGraph agent graph.

    Returns (compiled_graph, tools_list) so the caller can inspect tools.
    """
    if max_iterations is None:
        max_iterations = int(getattr(settings, "agent_max_iterations", 5))

    tools = make_tools(db)

    model_name = getattr(settings, "agent_model_name", "qwen/qwen3.8-27b")
    llm = ChatGroq(
        model=model_name,
        api_key=settings.groq_api_key,
        temperature=0,
        max_tokens=4096,
    )
    llm_with_tools = llm.bind_tools(tools)

    tool_node = ToolNode(tools)

    # ── Node functions ────────────────────────────────────────

    async def agent_node(state: AgentState) -> dict:
        """Invoke the LLM (with tools bound)."""
        messages = state["messages"]
        response = await llm_with_tools.ainvoke(messages)

        # Log tool calls if any
        log = state.get("tool_calls_log", [])
        if response.tool_calls:
            for tc in response.tool_calls:
                log.append({
                    "tool": tc["name"],
                    "args": tc["args"],
                    "result_summary": None,  # filled after tool execution
                })

        # Extract paper IDs from the response content
        paper_ids = state.get("retrieved_paper_ids", [])
        if isinstance(response.content, str):
            found = re.findall(r"paper_id=(\d+)", response.content)
            paper_ids = list(set(paper_ids + [int(x) for x in found]))

        return {
            "messages": [response],
            "tool_calls_log": log,
            "iterations": state.get("iterations", 0) + 1,
            "retrieved_paper_ids": paper_ids,
        }

    async def tools_node(state: AgentState) -> dict:
        """Execute tools via the prebuilt ToolNode and log results."""
        result = await tool_node.ainvoke(state)

        # Update log with result summaries
        log = state.get("tool_calls_log", [])
        new_messages = result.get("messages", [])
        for msg in new_messages:
            content_str = str(msg.content) if hasattr(msg, "content") else str(msg)
            summary = content_str[:200] + "..." if len(content_str) > 200 else content_str
            # Find the last log entry without a result_summary
            for entry in reversed(log):
                if entry["result_summary"] is None:
                    entry["result_summary"] = summary
                    break

        # Extract paper IDs from tool results
        paper_ids = state.get("retrieved_paper_ids", [])
        for msg in new_messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                found = re.findall(r"paper_id=(\d+)", msg.content)
                paper_ids = list(set(paper_ids + [int(x) for x in found]))

        return {
            "messages": new_messages,
            "tool_calls_log": log,
            "retrieved_paper_ids": paper_ids,
        }

    async def verify_node(state: AgentState) -> dict:
        """Verify that cited paper IDs in the final answer exist in the DB."""
        warnings = []
        last_msg = state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else ""

        if not isinstance(content, str):
            return {"warnings": warnings}

        # Find all paper_id references in the final answer
        cited_ids = [int(x) for x in re.findall(r"paper_id=(\d+)", content)]
        retrieved_ids = set(state.get("retrieved_paper_ids", []))

        for pid in cited_ids:
            if pid not in retrieved_ids:
                # Check DB directly
                result = await db.execute(
                    select(Paper.id).where(Paper.id == pid)
                )
                if result.scalar_one_or_none() is None:
                    warnings.append(
                        f"Citation paper_id={pid} not found in the database. "
                        "This may be a hallucinated reference."
                    )

        return {"warnings": warnings}

    # ── Routing logic ─────────────────────────────────────────

    def should_continue(state: AgentState) -> str:
        """Route: if the LLM made tool calls and we're under the cap, go to tools."""
        last_msg = state["messages"][-1]
        iterations = state.get("iterations", 0)

        if iterations >= max_iterations:
            return "verify"

        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"

        return "verify"

    # ── Build graph ───────────────────────────────────────────

    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("verify", verify_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "verify": "verify",
    })
    workflow.add_edge("tools", "agent")
    workflow.add_edge("verify", END)

    graph = workflow.compile()
    return graph, tools
