"""Agent API router — POST /api/v1/agent/ask."""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, SystemMessage

from app.db.session import get_db
from app.services.agent.graph import build_agent_graph, AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Research Agent"])


# ── Schemas ──────────────────────────────────────────────────

class AgentAskRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)


class AgentCitation(BaseModel):
    paper_id: int
    title: str | None = None


class AgentStep(BaseModel):
    tool: str
    args: dict[str, Any]
    result_summary: str | None


class AgentAskResponse(BaseModel):
    answer: str
    citations: list[AgentCitation]
    steps: list[AgentStep]
    iterations: int
    warnings: list[str]
    latency_seconds: float


# ── Endpoint ─────────────────────────────────────────────────

@router.post("/ask", response_model=AgentAskResponse)
async def agent_ask(request: AgentAskRequest, db: AsyncSession = Depends(get_db)):
    """
    Ask the research agent a question. The agent uses tools (semantic search,
    paper lookup, similarity search, literature review) to gather evidence
    before answering. Citations are verified against the database.
    """
    start = time.time()

    try:
        graph, tools = build_agent_graph(db)

        # Run the graph
        initial_state = {
            "messages": [
                SystemMessage(content=AGENT_SYSTEM_PROMPT),
                HumanMessage(content=request.question),
            ],
            "tool_calls_log": [],
            "iterations": 0,
            "retrieved_paper_ids": [],
            "warnings": [],
        }

        result = await graph.ainvoke(initial_state)

        # Extract the final answer (last AI message)
        answer = ""
        for msg in reversed(result["messages"]):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                # Skip tool messages
                if msg.type in ("ai", "AIMessage") or (hasattr(msg, "type") and msg.type == "ai"):
                    answer = msg.content
                    break
        if not answer:
            # Fallback: get last message with content
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                    answer = msg.content
                    break

        # Build citations from retrieved paper IDs
        import re
        from sqlalchemy import select
        from app.db.models import Paper

        cited_ids = set()
        if answer:
            cited_ids = {int(x) for x in re.findall(r"paper_id=(\d+)", answer)}

        citations = []
        for pid in cited_ids:
            r = await db.execute(select(Paper.id, Paper.title).where(Paper.id == pid))
            row = r.first()
            if row:
                citations.append(AgentCitation(paper_id=row.id, title=row.title))

        # Build steps
        steps = [
            AgentStep(
                tool=entry["tool"],
                args=entry["args"],
                result_summary=entry.get("result_summary"),
            )
            for entry in result.get("tool_calls_log", [])
        ]

        latency = time.time() - start

        return AgentAskResponse(
            answer=answer,
            citations=citations,
            steps=steps,
            iterations=result.get("iterations", 0),
            warnings=result.get("warnings", []),
            latency_seconds=round(latency, 2),
        )

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}",
        )
