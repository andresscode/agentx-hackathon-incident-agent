# 🚨 SRE Incident Agent — AgentX Hackathon

> Intelligent SRE incident intake and classification agent for e-commerce applications, featuring automated triage, ticket management, end-to-end notifications, and full observability.

---

## 📋 Project Overview

A multi-agent system that ingests incident reports (text, images, logs, video), performs automated triage by analyzing code and documentation, creates tickets in the chosen ticketing system, notifies the engineering team, and closes the loop by notifying the original reporter once the incident is resolved.

Built for the **AgentX Hackathon** — [#AgentXHackathon](https://youtube.com)

---

## 🔄 Core End-to-End Flow

```
[Reporter]
    │
    ▼ (1) Submits multimodal report (text + image/log/video)
┌─────────────────────────────────────────────────────┐
│               Frontend — Next.js                    │
└─────────────────────────────────────────────────────┘
    │
    ▼ (2) Automated triage
┌─────────────────────────────────────────────────────┐
│          SRE Agent — FastAPI + LangGraph            │
│  · Extracts key incident details                    │
│  · Analyzes e-commerce repo code & documentation    │
│  · Generates technical summary + severity score     │
│  · Prompt injection protection                      │
└─────────────────────────────────────────────────────┘
    │
    ├──▶ (3) Creates ticket in Jira / Linear / Peppermint
    │
    ├──▶ (4) Notifies engineering team (Email + Slack)
    │
    ▼ (5) Ticket resolved → notifies original reporter
[Reporter] ◀───────────────────────────────────────────
```

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│        Backend           │────▶│   PostgreSQL    │
│  Next.js +      │     │  FastAPI + Python (UV)   │     │  + pgvector     │
│  Tailwind CSS   │     │  LangChain / LangGraph   │     └─────────────────┘
│  shadcn/ui      │     └──────────────────────────┘
└─────────────────┘              │
                     ┌───────────┼─────────────┐
                     ▼           ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌───────────────┐
              │ Ticketing│ │  Email + │ │ Observability │
              │Jira/Linear│ │  Slack  │ │LangFuse/Phoenix│
              └──────────┘ └──────────┘ └───────────────┘
```

### Tech Stack

| Layer               | Technology                                                   |
|---------------------|--------------------------------------------------------------|
| **Frontend**        | Next.js + Tailwind CSS + shadcn/ui                           |
| **Backend / API**   | FastAPI + Python + UV                                        |
| **AI Agents**       | LangChain / LangGraph                                        |
| **Models**          | Multimodal LLM via API (Anthropic / GCP Vertex / OpenRouter) |
| **Database**        | PostgreSQL + pgvector                                        |
| **Ticketing**       | Jira / Linear / Peppermint (open source)                     |
| **Notifications**   | Email + Slack                                                |
| **Observability**   | LangFuse / Phoenix (Arize)                                   |
| **Containers**      | Docker Compose                                               |
| **E-commerce repo** | _(mid/full complexity open source — see `AGENTS_USE.md`)_    |


---

## 🚀 Quickstart

### Prerequisites
- Node.js 20+, pnpm
- Python 3.12+, uv
- Docker & Docker Compose

```bash
# 1. Clone the repository
git clone https://github.com/andresscode/agentx-hackathon-incident-agent.git
cd agentx-hackathon-incident-agent

# 2. Copy environment variables and fill in your keys
cp .env.example .env

# 3. Start all services
docker compose up --build

# Services available at:
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
```

> See [`QUICKGUIDE.md`](./QUICKGUIDE.md) for detailed step-by-step instructions.

### Local Development (without Docker)

**Database**
```bash
docker compose up db
```

**Backend**
```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

---

## 📁 Repository Structure

```
.
├── frontend/              # Next.js + Tailwind
├── backend/
│   ├── agents/            # LangGraph orchestration — SRE agent
│   ├── api/               # FastAPI endpoints
│   ├── integrations/      # Ticketing, Email, Slack
│   └── db/                # PostgreSQL models + pgvector
├── docker-compose.yml
├── .env.example
├── README.md              # This file
├── AGENTS_USE.md          # Use cases, implementation & security
├── SCALING.md             # Scalability & technical decisions
├── QUICKGUIDE.md          # Quick run guide
└── LICENSE                # MIT
```

---

## 🔒 Security & Responsible AI

- **Prompt injection protection**: inputs are validated and sanitized before reaching the LLM.
- **Safe tool usage**: agents operate with minimum required permissions.
- **Privacy**: sensitive incident data is not logged in plain text.
- **Transparency**: every agent decision is traceable via LangFuse/Phoenix.
- **Fairness & accountability**: aligned with the hackathon's responsible AI principles.

---

## 📊 Observability

Trace coverage across all pipeline stages:

| Stage         | Captured Metrics                      | 
|---------------|---------------------------------------|                      
| Ingestion     | Input received, modality, size        |
| Triage        | Tokens used, model, assigned severity |
| Ticket        | Created ID, target system, latency    |
| Notification  | Channel, recipient, delivery status   |
| Resolution    | Total time, responsible agent         |

---

## 🌿 Git Workflow

- **`main`** — stable branch
- **`develop`** — feature integration
- **`feature/<name>`** — one branch per task, created from `develop`

---

## 👥 Team

| Handle            | Role                          |
|-------------------|-------------------------------|
| `@joedoe6179`     | Team Lead / Full Stack        |
| `@ouroboroz333`   | Backend / AI / Infrastructure |
| `@_kindalikedeus` | Architecture / Scaling        |
| `@happier_helmut` | Documentation / Backend       |

---

## 📄 License

[MIT](./LICENSE)