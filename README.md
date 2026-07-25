<div align="center">
  <img src="docs/logo.svg" alt="PaperMind Logo" width="80" />
  <h1>PaperMind</h1>
  <p><strong>AI-Powered Research Intelligence Platform</strong></p>
  <p>Discover, analyze, and explore academic papers using semantic search, knowledge graphs, and RAG-powered Q&A.</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react" alt="React" />
    <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/Groq-LLM-orange?style=flat-square" alt="Groq" />
  </p>
</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Semantic Search** | Search papers by meaning, not keywords — powered by sentence transformers + pgvector |
| 🧠 **RAG Q&A** | Ask questions about your paper collection — grounded answers with zero hallucination |
| 📊 **Research Analytics** | Interactive dashboards with publication trends, field distributions, and venue analysis |
| 🕸️ **Knowledge Graph** | Visual similarity network showing topic clusters — node size = citations, color = year |
| 📝 **Literature Reviews** | AI-generated reviews in 4 styles: comprehensive, brief, gap analysis, and trend reports |
| 📥 **Topic Ingestion** | Bulk-fetch papers from Semantic Scholar with one click — abstracts auto-embedded |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│  ┌──────────┐ ┌────────┐ ┌───────┐ ┌─────────┐ ┌────────┐  │
│  │ Discover │ │ Search │ │ Graph │ │Analytics│ │ Ask AI │  │
│  └────┬─────┘ └───┬────┘ └───┬───┘ └────┬────┘ └───┬────┘  │
│       └───────────┴──────────┴───────────┴──────────┘       │
│                           REST API                           │
├─────────────────────────────────────────────────────────────┤
│                   Backend (FastAPI + Python)                  │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ Ingestion │  │ Embedding    │  │ Q&A Service          │   │
│  │ Service   │  │ Service      │  │ (Groq LLM + RAG)    │   │
│  └─────┬─────┘  └──────┬───────┘  └─────────┬───────────┘   │
│        │               │                    │                │
│  ┌─────┴───────────────┴────────────────────┴───────────┐   │
│  │              SQLAlchemy Async ORM                      │   │
│  └───────────────────────┬───────────────────────────────┘   │
├──────────────────────────┼──────────────────────────────────┤
│                          │                                   │
│  ┌───────────────────────▼───────────────┐  ┌────────────┐  │
│  │  PostgreSQL + pgvector (Neon.tech)     │  │ Redis      │  │
│  │  • Papers, Authors, Citations          │  │ (Upstash)  │  │
│  │  • 384-dim embedding vectors           │  │            │  │
│  └───────────────────────────────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL with pgvector (or [Neon.tech](https://neon.tech) free tier)
- Redis (or [Upstash](https://upstash.com) free tier)
- [Groq API Key](https://console.groq.com/keys) (free)

### 1. Clone & Setup

```bash
git clone https://github.com/your-username/papermind.git
cd papermind

# Backend
cd backend
cp .env.example .env
# Edit .env with your credentials
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Database Setup

If using Neon.tech, run in the SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Run

```bash
# Terminal 1 — Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** and start exploring!

## 📦 Tech Stack

### Backend
- **FastAPI** — async REST API with auto-generated OpenAPI docs
- **SQLAlchemy 2.0** — async ORM with relationship mapping
- **pgvector** — vector similarity search inside PostgreSQL
- **sentence-transformers** — `all-MiniLM-L6-v2` for 384-dim embeddings
- **Groq** — ultra-fast LLM inference (Llama 3.1)
- **Celery** — optional async task queue for background ingestion

### Frontend
- **React 18** — component-based UI with hooks
- **Vite** — lightning-fast HMR and builds
- **Recharts** — responsive data visualization
- **vis-network** — force-directed graph rendering
- **Axios** — HTTP client

### Infrastructure
- **Neon.tech** — serverless PostgreSQL with pgvector
- **Upstash** — serverless Redis for caching
- **Render** — backend hosting
- **Vercel** — frontend hosting

## 📁 Project Structure

```
papermind/
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers (papers, search, qa, review)
│   │   ├── core/          # Config, Celery, settings
│   │   ├── db/            # SQLAlchemy models + session
│   │   └── services/      # Business logic
│   │       ├── embeddings.py        # Sentence transformer embedding
│   │       ├── ingestion.py         # Paper fetch + store pipeline
│   │       ├── semantic_scholar.py  # S2 API client
│   │       └── qa.py               # RAG question answering
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/         # React page components
│   │   ├── api.js         # API client
│   │   ├── App.jsx        # Router + layout
│   │   └── index.css      # Design system
│   └── package.json
└── README.md
```

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | ✅ |
| `REDIS_URL` | Redis/Upstash connection | ✅ |
| `GROQ_API_KEY` | Groq API key for LLM | ✅ |
| `SEMANTIC_SCHOLAR_API_KEY` | S2 API key (higher rate limits) | ❌ |
| `EMBEDDING_MODEL_NAME` | HuggingFace model ID | ❌ |

## 📸 Screenshots

### Discover & Ingest
Fetch papers from Semantic Scholar with one click. See real-time stats and publication trends.

### Semantic Search
Search by meaning — "attention mechanisms for fusing audio and text" finds relevant papers even without exact keyword matches.

### Knowledge Graph
Interactive force-directed graph showing semantic similarity clusters. Edge thickness = similarity strength.

### Analytics Dashboard
6 interactive charts: publication volume, cumulative growth, field distribution, open access ratio, top authors, and top venues.

### RAG Q&A
Ask research questions grounded in your indexed papers. Every answer cites specific papers — no hallucination.

### Literature Review
AI-generated reviews in 4 styles: comprehensive, brief overview, research gaps, and trend analysis.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">
  <p>Built with 💜 by Ankit Yadav</p>
</div>
