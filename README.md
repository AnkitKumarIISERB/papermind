<div align="center">
  <h1>🧠 PaperMind</h1>
  <p><strong>AI-Powered Research Intelligence Platform</strong></p>
  <p>Discover, analyze, and explore academic papers using semantic search, knowledge graphs, and RAG-powered Q&A — all grounded in retrieved abstracts.</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
    <img src="https://img.shields.io/badge/pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="pgvector" />
    <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph" />
    <img src="https://img.shields.io/badge/Groq_LLM-orange?style=for-the-badge" alt="Groq" />
  </p>

  <h3>
    <a href="https://papermind-lemon.vercel.app" target="_blank">🌐 Try the Live Demo</a>
  </h3>
</div>

<br/>

## 📸 Screenshots

<table>
  <tr>
    <td align="center"><strong>Discover & Stats</strong></td>
    <td align="center"><strong>Knowledge Graph</strong></td>
  </tr>
  <tr>
    <td><img src="docs/discover.png" width="450"/></td>
    <td><img src="docs/graph.png" width="450"/></td>
  </tr>
  <tr>
    <td align="center" colspan="2"><strong>Analytics Dashboard</strong></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="docs/analytics.png" width="700"/></td>
  </tr>
</table>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Semantic Search** | Search papers by meaning, not keywords — powered by sentence transformers + pgvector cosine similarity |
| 🧠 **RAG Q&A** | Ask questions about your paper collection — grounded answers citing specific papers |
| 🤖 **Agent Mode** | LangGraph-based research agent with multi-step tool calling — searches, retrieves, and reasons over papers before answering |
| 📊 **Research Analytics** | 6 interactive charts: publication trends, cumulative growth, field distribution, open access ratio, top authors, top venues |
| 🕸️ **Knowledge Graph** | Force-directed similarity network — papers with similar embeddings are connected, node size = citations, color = year |
| 📝 **Literature Reviews** | AI-generated reviews in 4 styles: comprehensive, brief overview, research gaps, and trend analysis |
| 📥 **Topic Ingestion** | Bulk-fetch papers from Semantic Scholar with one click — abstracts auto-embedded into 384-dim vectors |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                      │
│  ┌──────────┐ ┌────────┐ ┌───────┐ ┌─────────┐ ┌────────────┐  │
│  │ Discover │ │ Search │ │ Graph │ │Analytics│ │ Ask AI     │  │
│  │          │ │        │ │       │ │         │ │ (RAG/Agent)│  │
│  └────┬─────┘ └───┬────┘ └───┬───┘ └────┬────┘ └─────┬──────┘  │
│       └───────────┴──────────┴───────────┴────────────┘         │
│                           REST API                               │
├─────────────────────────────────────────────────────────────────┤
│                    Backend (FastAPI + Python)                     │
│  ┌───────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ Ingestion │ │ Embedding  │ │ Q&A (RAG)  │ │ Agent        │  │
│  │ Service   │ │ Service    │ │ Groq LLM   │ │ (LangGraph)  │  │
│  └─────┬─────┘ └─────┬──────┘ └──────┬─────┘ └──────┬───────┘  │
│        │             │               │              │           │
│  ┌─────┴─────────────┴───────────────┴──────────────┴───────┐  │
│  │                  SQLAlchemy Async ORM                      │  │
│  └──────────────────────────┬─────────────────────────────────┘  │
├─────────────────────────────┼───────────────────────────────────┤
│                             │                                    │
│  ┌──────────────────────────▼──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL + pgvector (Neon.tech)       │  │ Redis        │  │
│  │  • Papers, Authors, Citations            │  │ (Upstash)    │  │
│  │  • 384-dim embedding vectors             │  │              │  │
│  └─────────────────────────────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Key Engineering Decisions

### 1. Similarity-Based Knowledge Graph
Traditional citation graphs require expensive API calls per paper. Instead, PaperMind computes **cosine similarity between paper embeddings** directly in PostgreSQL using pgvector's `<=>` operator, creating meaningful topic clusters with a single SQL query:
```sql
SELECT e1.paper_id, e2.paper_id, 1 - (e1.embedding <=> e2.embedding) AS similarity
FROM paper_embeddings e1
JOIN paper_embeddings e2 ON e1.paper_id < e2.paper_id
WHERE 1 - (e1.embedding <=> e2.embedding) > 0.55
```

### 2. RAG Over Hallucination
The Q&A system retrieves the top-K most relevant paper abstracts via vector similarity search, then feeds them as context to the LLM via Groq. The model is instructed to only cite papers from the provided context — grounded in retrieved abstracts, not training data.

### 3. LangGraph Research Agent
The Agent Mode adds a multi-step reasoning layer via [LangGraph](https://langchain-ai.github.io/langgraph/). Instead of single-shot RAG, an LLM decides which tools to call (semantic search, paper lookup, similarity search, literature review), iterates up to 5 times, and verifies citations before returning an answer.

```mermaid
graph LR
    A[User Question] --> B[Agent Node<br>ChatGroq + bind_tools]
    B -->|tool_calls| C[Tool Node<br>search / get_paper / similar / review]
    C --> B
    B -->|no tool_calls| D[Verify Node<br>Check cited paper IDs exist]
    D --> E[Response<br>answer + citations + steps]
```

**Tools available:**
| Tool | Description |
|------|-------------|
| `search_papers(query, k)` | Semantic search over paper abstracts |
| `get_paper(paper_id)` | Full metadata + abstract for one paper |
| `find_similar_papers(paper_id, k)` | Nearest neighbors via pgvector cosine |
| `generate_review(topic)` | Literature review using retrieved papers |

**Endpoint:** `POST /api/v1/agent/ask` with `{"question": "..."}` → returns `{answer, citations, steps, iterations, warnings}`

### 4. Sync Fallback for Celery
The ingestion pipeline supports both async (Celery + Redis) and synchronous execution. When Celery workers aren't available, the `/ingest` endpoint runs the full pipeline in-process — enabling single-command local development without Docker.

---

## 📦 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI + async SQLAlchemy 2.0 | Non-blocking REST endpoints |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` | 384-dim paper abstract vectors |
| **Vector Search** | pgvector | Cosine similarity inside PostgreSQL |
| **LLM** | Groq (Qwen 3.8 27B) | Free-tier inference; 131K context for Q&A and agent tool-calling |
| **Agent** | LangGraph + langchain-groq | Multi-step tool-calling research agent |
| **Frontend** | React 18 + Vite + Recharts + vis-network | 6-page SPA with interactive graphs |
| **Database** | Neon.tech (serverless PostgreSQL) | Free-tier cloud Postgres with pgvector |
| **Cache** | Upstash (serverless Redis) | Task queue and caching |
| **Hosting** | Render (backend) + Vercel (frontend) | $0/month deployment |

---

## 📂 Project Structure

```
papermind/
├── backend/
│   ├── app/
│   │   ├── api/                   # REST route handlers
│   │   │   ├── papers.py          # Ingest, list, graph, stats
│   │   │   ├── search.py          # Semantic search + Q&A
│   │   │   ├── agent.py           # POST /agent/ask endpoint
│   │   │   └── collections.py     # Paper collections CRUD
│   │   ├── core/                  # Config + Celery
│   │   ├── db/                    # SQLAlchemy models + async session
│   │   └── services/              # Business logic
│   │       ├── embeddings.py      # Sentence transformer pipeline
│   │       ├── ingestion.py       # S2 fetch → store → embed
│   │       ├── search.py          # Semantic search + QA retrieval
│   │       ├── semantic_scholar.py # API client with rate limiting
│   │       ├── groq_llm.py        # RAG Q&A + literature review
│   │       └── agent/             # LangGraph research agent
│   │           ├── __init__.py
│   │           ├── tools.py       # @tool wrappers over services
│   │           └── graph.py       # StateGraph + verify node
│   ├── eval/
│   │   └── agent_eval.py          # Agent vs RAG evaluation harness
│   ├── tests/
│   │   └── test_agent.py          # 7 unit tests for agent
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── pages/                 # 6 React page components
│       ├── api.js                 # Axios API client
│       ├── App.jsx                # Router + nav
│       └── index.css              # Design system
├── render.yaml                    # Render deployment config
└── README.md
```

---

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | ✅ |
| `REDIS_URL` | Redis/Upstash connection | ✅ |
| `GROQ_API_KEY` | Groq API key for LLM ([free](https://console.groq.com/keys)) | ✅ |
| `GROQ_MODEL` | Model for RAG Q&A (default: `qwen/qwen3.8-27b`) | ❌ |
| `SEMANTIC_SCHOLAR_API_KEY` | S2 API key for higher rate limits | ❌ |
| `EMBEDDING_MODEL_NAME` | HuggingFace model ID (default: `all-MiniLM-L6-v2`) | ❌ |
| `AGENT_MODEL_NAME` | LLM for agent tool-calling (default: `qwen/qwen3.8-27b`) | ❌ |
| `AGENT_MAX_ITERATIONS` | Max agent tool-call loops (default: 5) | ❌ |

---

## 🚀 Quick Start

```bash
git clone https://github.com/AnkitKumarIISERB/papermind.git
cd papermind

# Backend
cd backend
cp .env.example .env        # Edit with your credentials
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd ../frontend
npm install
npm run dev
```

Open **http://localhost:5173** → enter a research topic → click "Fetch Papers" → explore!

---

## ⚠️ Known Limitations

1. **Render Cold Starts**: Free-tier backend sleeps after 15 min of inactivity. First request takes ~30s to wake.
2. **Semantic Scholar Rate Limits**: Without an API key, limited to 100 requests/5 min. The ingestion pipeline auto-retries with backoff.
3. **CPU-Only Embeddings**: sentence-transformers runs on CPU (~0.5s per abstract). GPU would be 10x faster but isn't available on free hosting.
4. **Agent Tool-Calling**: Qwen 3.8 27B on Groq free tier handles tool calls well. Smaller models may be flaky with structured tool calls.
5. **5-Step Agent Cap**: Complex multi-hop questions may be truncated. The agent stops after 5 iterations to prevent runaway loops.
6. **Abstracts Only**: The agent searches over paper abstracts, not full text. Claims about specific experiments or tables may be incomplete.

---

<div align="center">
  <p>Built with 💜 by Ankit</p>
</div>
