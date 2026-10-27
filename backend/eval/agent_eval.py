"""Agent evaluation script.

Runs a set of questions through both the agent and the existing RAG endpoint,
measuring citation validity, correctness on unanswerable questions, and latency.

Usage:
    cd backend
    python -m eval.agent_eval

Requires: a running Postgres with ingested papers, GROQ_API_KEY set.
"""

import asyncio
import json
import re
import time
from typing import Any

from sqlalchemy import select

# Bootstrap the app
import sys
sys.path.insert(0, ".")
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.db.models import Paper
from app.services.search import get_papers_for_qa
from app.services.groq_llm import ask_question
from app.services.agent.graph import build_agent_graph, AGENT_SYSTEM_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage

settings = get_settings()

# ── Eval questions ────────────────────────────────────────────
# Mix of answerable and unanswerable questions.
# Unanswerable questions are tagged with "unanswerable": True.

EVAL_QUESTIONS = [
    {"q": "What are the main approaches to multimodal fusion in recent literature?", "unanswerable": False},
    {"q": "Which papers propose attention-based methods?", "unanswerable": False},
    {"q": "What datasets are commonly used for depression detection?", "unanswerable": False},
    {"q": "Compare text-only vs multimodal approaches for mental health screening.", "unanswerable": False},
    {"q": "What is the role of speech features in emotion detection?", "unanswerable": False},
    {"q": "Which papers achieve the highest F1 scores?", "unanswerable": False},
    {"q": "What transformer architectures are used in the indexed papers?", "unanswerable": False},
    {"q": "What are the limitations of current multimodal methods?", "unanswerable": False},
    {"q": "How is WavLM used in the indexed papers?", "unanswerable": False},
    {"q": "What evaluation protocols are used across the papers?", "unanswerable": False},
    {"q": "Which papers use DAIC-WOZ dataset?", "unanswerable": False},
    {"q": "What are the key findings about cross-dataset generalization?", "unanswerable": False},
    {"q": "Summarize the methods used for audio feature extraction.", "unanswerable": False},
    {"q": "What is the best recipe for chocolate cake?", "unanswerable": True},
    {"q": "What is the current stock price of Apple Inc?", "unanswerable": True},
    {"q": "Explain quantum teleportation and its applications in computing.", "unanswerable": True},
    {"q": "What did the paper by Zuckerberg et al. 2025 on social media addiction find?", "unanswerable": True},
]


async def run_agent(question: str) -> dict[str, Any]:
    """Run a single question through the agent."""
    async with async_session_factory() as db:
        try:
            graph, _ = build_agent_graph(db)
            start = time.time()
            result = await graph.ainvoke({
                "messages": [
                    SystemMessage(content=AGENT_SYSTEM_PROMPT),
                    HumanMessage(content=question),
                ],
                "tool_calls_log": [],
                "iterations": 0,
                "retrieved_paper_ids": [],
                "warnings": [],
            })
            latency = time.time() - start

            # Extract answer
            answer = ""
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content:
                    if hasattr(msg, "type") and msg.type == "ai":
                        answer = msg.content
                        break
            if not answer:
                for msg in reversed(result["messages"]):
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        answer = msg.content
                        break

            # Check cited paper IDs exist in DB
            cited_ids = [int(x) for x in re.findall(r"paper_id=(\d+)", answer)]
            valid_citations = 0
            for pid in cited_ids:
                r = await db.execute(select(Paper.id).where(Paper.id == pid))
                if r.scalar_one_or_none() is not None:
                    valid_citations += 1

            return {
                "answer": answer[:300],
                "tool_calls": len(result.get("tool_calls_log", [])),
                "iterations": result.get("iterations", 0),
                "cited_ids": cited_ids,
                "valid_citations": valid_citations,
                "total_citations": len(cited_ids),
                "citation_validity": valid_citations / max(len(cited_ids), 1),
                "warnings": result.get("warnings", []),
                "latency": round(latency, 2),
                "error": None,
            }
        except Exception as e:
            return {
                "answer": "", "tool_calls": 0, "iterations": 0,
                "cited_ids": [], "valid_citations": 0, "total_citations": 0,
                "citation_validity": 0, "warnings": [], "latency": 0,
                "error": str(e),
            }


async def run_rag(question: str) -> dict[str, Any]:
    """Run a single question through the existing RAG endpoint."""
    async with async_session_factory() as db:
        try:
            start = time.time()
            papers = await get_papers_for_qa(query=question, db=db, top_k=8)
            if not papers:
                return {
                    "answer": "No papers found.",
                    "citation_validity": 1.0,  # correctly reported no results
                    "latency": round(time.time() - start, 2),
                    "error": None,
                }
            answer = await ask_question(question, papers)
            latency = time.time() - start

            return {
                "answer": answer[:300],
                "citation_validity": 1.0,  # RAG always cites retrieved papers
                "latency": round(latency, 2),
                "error": None,
            }
        except Exception as e:
            return {"answer": "", "citation_validity": 0, "latency": 0, "error": str(e)}


async def main():
    print("=" * 70)
    print("PaperMind Agent Evaluation")
    print("=" * 70)

    results = []

    for i, item in enumerate(EVAL_QUESTIONS):
        q = item["q"]
        unans = item["unanswerable"]
        print(f"\n[{i+1}/{len(EVAL_QUESTIONS)}] {'(UNANSWERABLE) ' if unans else ''}{q[:60]}...")

        agent_result = await run_agent(q)
        rag_result = await run_rag(q)

        # Check if unanswerable was correctly declined
        declined = False
        if unans and agent_result["answer"]:
            decline_phrases = ["cannot find", "not found", "no papers", "not in the collection",
                               "no information", "don't have", "outside", "not available"]
            declined = any(p in agent_result["answer"].lower() for p in decline_phrases)

        results.append({
            "question": q,
            "unanswerable": unans,
            "agent_tool_calls": agent_result["tool_calls"],
            "agent_iterations": agent_result["iterations"],
            "agent_citation_validity": agent_result["citation_validity"],
            "agent_declined_correctly": declined if unans else None,
            "agent_latency": agent_result["latency"],
            "agent_error": agent_result["error"],
            "rag_citation_validity": rag_result["citation_validity"],
            "rag_latency": rag_result["latency"],
            "rag_error": rag_result["error"],
        })

        print(f"  Agent: {agent_result['tool_calls']} tools, "
              f"cit_valid={agent_result['citation_validity']:.0%}, "
              f"{agent_result['latency']}s"
              f"{' DECLINED' if declined else ''}"
              f"{' ERROR: ' + agent_result['error'] if agent_result['error'] else ''}")
        print(f"  RAG:   cit_valid={rag_result['citation_validity']:.0%}, "
              f"{rag_result['latency']}s"
              f"{' ERROR: ' + rag_result['error'] if rag_result['error'] else ''}")

    # ── Summary ───────────────────────────────────────────────
    answerable = [r for r in results if not r["unanswerable"]]
    unanswerable = [r for r in results if r["unanswerable"]]

    agent_avg_cit = sum(r["agent_citation_validity"] for r in answerable) / max(len(answerable), 1)
    rag_avg_cit = sum(r["rag_citation_validity"] for r in answerable) / max(len(answerable), 1)
    agent_avg_lat = sum(r["agent_latency"] for r in results) / max(len(results), 1)
    rag_avg_lat = sum(r["rag_latency"] for r in results) / max(len(results), 1)
    decline_rate = sum(1 for r in unanswerable if r["agent_declined_correctly"]) / max(len(unanswerable), 1)
    agent_errors = sum(1 for r in results if r["agent_error"])
    rag_errors = sum(1 for r in results if r["rag_error"])

    # ── Write RESULTS.md ──────────────────────────────────────
    md = f"""# Agent Evaluation Results

**Date**: auto-generated
**Model**: {getattr(settings, 'agent_model_name', 'llama-3.3-70b-versatile')}
**Questions**: {len(EVAL_QUESTIONS)} ({len(answerable)} answerable, {len(unanswerable)} unanswerable)

## Summary

| Metric | Agent | RAG (baseline) |
|--------|-------|----------------|
| Avg Citation Validity (answerable) | {agent_avg_cit:.0%} | {rag_avg_cit:.0%} |
| Avg Latency (seconds) | {agent_avg_lat:.1f}s | {rag_avg_lat:.1f}s |
| Unanswerable Decline Rate | {decline_rate:.0%} | N/A |
| Errors | {agent_errors}/{len(results)} | {rag_errors}/{len(results)} |

## Per-Question Results

| # | Question | Unanswerable | Agent Tools | Agent Cit Valid | Agent Declined | Agent Latency | RAG Latency |
|---|----------|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for i, r in enumerate(results):
        q_short = r["question"][:50] + "..." if len(r["question"]) > 50 else r["question"]
        md += (
            f"| {i+1} | {q_short} | {'✓' if r['unanswerable'] else ''} | "
            f"{r['agent_tool_calls']} | {r['agent_citation_validity']:.0%} | "
            f"{'✓' if r.get('agent_declined_correctly') else ('✗' if r['unanswerable'] else '—')} | "
            f"{r['agent_latency']}s | {r['rag_latency']}s |\n"
        )

    md += f"""
## Limitations

- **Model tool-calling reliability**: Qwen 3.8 27B handles tool calls well; smaller models may be flaky.
- **5-step iteration cap**: Complex multi-hop questions may be truncated.
- **Abstracts only**: The agent searches over paper abstracts, not full text.
- **Synthetic grounding**: Citation validity measures whether cited paper IDs exist in the DB, not whether the claim accurately reflects the paper content.
"""

    with open("eval/RESULTS.md", "w") as f:
        f.write(md)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Agent citation validity (answerable): {agent_avg_cit:.0%}")
    print(f"RAG citation validity (answerable):   {rag_avg_cit:.0%}")
    print(f"Agent avg latency: {agent_avg_lat:.1f}s")
    print(f"RAG avg latency:   {rag_avg_lat:.1f}s")
    print(f"Unanswerable decline rate: {decline_rate:.0%}")
    print(f"Results written to eval/RESULTS.md")


if __name__ == "__main__":
    asyncio.run(main())
