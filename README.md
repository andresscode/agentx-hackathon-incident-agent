# SRE Incident Intake & Triage Agent

> Intelligent SRE incident intake and triage agent for e-commerce applications, featuring automated classification, codebase-aware root cause analysis, ticket management, team notifications, and full observability.

Built for the **AgentX Hackathon**

---

## Core End-to-End Flow

```
[Reporter]
    |
    v  (1) Submits incident report (text + optional screenshot)
+---------------------------------------------------+
|              Frontend - Next.js                   |
|  Client-side validation (Zod + vard)              |
+---------------------------------------------------+
    |
    v  (2) Automated triage (background, 10-20 seconds)
+---------------------------------------------------+
|         SRE Triage Agent - FastAPI + LangGraph    |
|  . Prompt injection check (LLM security gate)     |
|  . Classifies: category, priority, severity, team |
|  . Searches Reaction Commerce codebase            |
|  . Generates technical triage report              |
+---------------------------------------------------+
    |
    |---> (3) Creates ticket in Peppermint
    |
    |---> (4) Notifies engineering team (Discord + Email via Apprise)
    |
    v  (5) Ticket resolved -> notifies original reporter
[Reporter] <-----------------------------------------
```

---

## Architecture

```
+-----------------+     +---------------------------+     +---------------+
|   Frontend      |---->|        Backend            |---->|  PostgreSQL   |
|  Next.js 15     |     |  FastAPI + LangGraph      |     +---------------+
|  React 19       |     |  LangChain                |
|  Tailwind CSS   |     +---------------------------+
|  shadcn/ui      |              |
+-----------------+   +----------+-----------+
                      v          v           v
               +----------+ +----------+ +-----------+
               |Peppermint| | Apprise  | |  Phoenix  |
               | (tickets)| | (Discord/| |  (OTEL    |
               |  :3001   | |  Email)  | |  traces)  |
               +----------+ +----------+ |   :6006   |
                                         +-----------+
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Zod |
| **Backend** | Python 3.12, FastAPI, LangGraph, LangChain, SQLAlchemy (async) |
| **Database** | PostgreSQL 16 |
| **LLM** | OpenAI, Anthropic, Google Gemini, OpenRouter, AI Gateway (configurable) |
| **Observability** | Arize Phoenix (OpenTelemetry), OpenInference LangChain instrumentation |
| **Ticketing** | Peppermint (open source) |
| **Notifications** | Apprise (Discord + email) |
| **Security** | Dual-layer prompt injection defense (vard client-side + LLM classifier server-side) |
| **E-commerce repo** | Reaction Commerce (Node.js, indexed at Docker build time) |
| **Infrastructure** | Docker Compose |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- An API key for at least one LLM provider

### 1. Configure environment

```bash
git clone https://github.com/andresscode/agentx-hackathon-incident-agent.git
cd agentx-hackathon-incident-agent
cp .env.example .env
```

Edit `.env` and set your LLM provider and API key:

```env
LLM_PROVIDER=openrouter          # openai | anthropic | google | openrouter | aigateway
OPENROUTER_API_KEY=sk-or-...     # only the key for your chosen provider is required
```

### 2. Start all services

```bash
docker compose up --build
```

First build takes ~2 minutes (clones and indexes the Reaction Commerce codebase).

### 3. Use the application

| Service | URL | Credentials |
|---------|-----|------------|
| **Incident Form** | http://localhost:3000 | -- |
| **Phoenix Traces** | http://localhost:6006 | -- |
| **Peppermint Tickets** | http://localhost:3001 | `admin@admin.com` / `1234` |

> See [`QUICKGUIDE.md`](./QUICKGUIDE.md) for a step-by-step evaluator walkthrough.

---

## Local Development

### Backend

```bash
cd backend
cp .env.example .env       # configure LLM provider + API key
docker compose up -d       # start PostgreSQL + Phoenix
uv sync                    # install dependencies
make dev                   # start FastAPI with hot reload (localhost:8000)
```

Make targets: `make dev` | `make lint` | `make typecheck`

### Frontend

```bash
cd frontend
cp .env.example .env       # set BACKEND_URL=http://localhost:8000
pnpm install
pnpm dev                   # start Next.js dev server (localhost:3000)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/incidents` | Create incident (multipart: name, email, description, image?) |
| GET | `/api/incidents/{id}` | Get incident with triage results |
| GET | `/api/incidents` | List all incidents (newest first) |
| GET | `/api/health` | Health check |

---

## Key Features

- **Multimodal input** -- text descriptions + image/screenshot uploads (PNG, JPEG, GIF, WebP)
- **AI-powered triage** -- automatic classification by category, priority, severity (1-10), and team routing
- **Codebase-aware** -- searches Reaction Commerce source code for relevant files, includes actual code snippets in reports
- **Structured LLM output** -- Pydantic models with constrained enums ensure consistent, parseable results
- **Prompt injection defense** -- dual-layer: client-side heuristic (vard) + server-side LLM classifier
- **Pluggable hooks** -- add integrations without modifying the triage pipeline
- **Multi-provider LLM** -- switch between 5 providers via a single environment variable
- **Full observability** -- Arize Phoenix traces every LLM call with tokens, latency, and prompt content

---

## Repository Structure

```
.
├── frontend/                 # Next.js 15 application
│   ├── src/app/              # Pages (incident form, success)
│   ├── src/components/       # UI components (incident-form, shadcn)
│   └── src/lib/              # Schemas, services, hooks, types
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── routes/           # API endpoints
│   │   ├── services/         # Business logic
│   │   ├── workflows/        # LangGraph triage pipeline + hooks
│   │   ├── schemas/          # Pydantic models for LLM structured output
│   │   ├── tools/            # Codebase search index
│   │   ├── models.py         # SQLAlchemy Incident model
│   │   ├── prompts.py        # All LLM system prompts
│   │   └── llm_provider.py   # Multi-provider LLM abstraction
│   └── scripts/              # Codebase indexing script
├── infrastructure/           # Standalone docker-compose files
├── docker-compose.yml        # Full-stack deployment
├── AGENTS_USE.md             # Agent documentation (hackathon template)
├── SCALING.md                # Scalability analysis
└── QUICKGUIDE.md             # Evaluator quick guide
```

---

## Security & Responsible AI

- **Prompt injection protection**: dual-layer defense -- client-side heuristic detection (vard) + server-side LLM classification with structured output
- **Safe input handling**: Zod + Pydantic validation at every boundary, file type/size restrictions
- **Tool safety**: agent has read-only access to codebase index, write access limited to ticket creation and notifications
- **Data handling**: API keys in environment variables wrapped in `SecretStr`, unsafe input never logged or exposed in responses
- **Transparency**: every agent decision is traceable via Arize Phoenix

---

## Observability

| Stage | What is traced |
|-------|---------------|
| Ingestion | Input received, prompt injection verdict, incident ID |
| Classification | Category, priority, severity, team, reasoning, tokens, latency |
| Codebase Search | Keywords, matched files, LLM file selection |
| Summary | Full triage report, tokens, latency |
| Hooks | Ticket creation, notification dispatch, success/failure |

All LLM calls are auto-instrumented via OpenInference + Phoenix OTEL.

---

## Git Workflow

- **`main`** -- stable branch
- **`develop`** -- feature integration
- **`feature/<name>`** -- one branch per task, created from `develop`

---

## Team

| Handle | Role |
|--------|------|
| `@joedoe6179` | Team Lead / Full Stack |
| `@ouroboroz333` | Backend / AI / Infrastructure |
| `@_kindalikedeus` | Architecture / Scaling |
| `@happier_helmut` | Documentation / Backend |

---

## Documentation

- [AGENTS_USE.md](AGENTS_USE.md) -- Agent implementation documentation (9-section hackathon template)
- [SCALING.md](SCALING.md) -- Scalability analysis and production roadmap
- [QUICKGUIDE.md](QUICKGUIDE.md) -- Quick start for evaluators

---

## License

[MIT](./LICENSE)
