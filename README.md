# LLMOps Gateway AI

**Intelligent multi-LLM routing, token optimization, and cost management platform.**

Built for AI/ML engineering and MLOps portfolios — demonstrates production-grade
multi-agent orchestration (LangGraph), full-stack observability, and cloud-native
deployment (Docker → Kubernetes → AWS EKS).

```
┌─────────┐    ┌──────────────┐    ┌─────────────────────────────────┐
│ Client  │───▶│ FastAPI      │───▶│ LangGraph Multi-Agent Pipeline   │
│         │    │ Gateway      │    │                                  │
└─────────┘    └──────────────┘    │ Security → Router → Token-Opt   │
                                    │   → Memory → Executor → Post    │
                                    └──────────────┬───────────────────┘
                                                   ▼
                          ┌──────────┬──────────┬──────────┬──────────┐
                          │ OpenAI   │Anthropic │ Gemini   │ Mistral  │
                          └──────────┴──────────┴──────────┴──────────┘
                                                   ▼
                     ┌───────────┬──────────┬───────────┬─────────────┐
                     │PostgreSQL │  Redis   │ ChromaDB  │ Prometheus  │
                     └───────────┴──────────┴───────────┴─────────────┘
```

## What this project demonstrates

| Area | Implementation |
|---|---|
| **Generative AI / Multi-Agent** | LangGraph `StateGraph` with 6 cooperating agents (security, routing, token optimization, memory/RAG, execution, post-processing) |
| **RAG** | ChromaDB + sentence-transformers for semantic conversation memory |
| **MLOps / Observability** | Prometheus metrics, Grafana dashboards, structured JSON logging, alert rules |
| **Backend Engineering** | FastAPI, async SQLAlchemy, JWT auth, Redis caching, rate limiting |
| **Security** | Prompt-injection detection, PII masking, encrypted API key storage |
| **DevOps** | Docker multi-stage builds, Docker Compose, Kubernetes manifests (HPA, PDB, Ingress), Terraform for AWS (EKS/RDS/ElastiCache/ECR) |
| **CI/CD** | GitHub Actions: lint → test → security scan → build → push to ECR → deploy to EKS → smoke test → auto-rollback |
| **Frontend** | React + Tailwind ops console with live request stream and routing visualizations |

---

## Quick start (Docker Compose)

```bash
git clone <your-repo-url>
cd llmops-gateway-ai
cp .env.example .env          # add at least one LLM provider API key
make docker-up
```

| Service | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (`admin` / `llmops_grafana`) |
| Frontend console | `cd frontend && npm install && npm run dev` → http://localhost:3001 |

## Quick start (local Python)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# start postgres + redis + chromadb yourself, or via:
docker-compose up -d postgres redis chromadb
alembic upgrade head
uvicorn backend.main:app --reload
```

## Current known issue and fix

- Issue: `POST /api/v1/llm/complete` could fail with `Internal error: run_agent_pipeline() got an unexpected keyword argument 'user_base_urls'`.
- Root cause: the backend route was passing `user_base_urls` into `run_agent_pipeline` without verifying the function signature, which caused a crash when the pipeline executor did not declare that parameter.
- Fix applied in `backend/api/routes/llm.py`:
  - collect `user_api_keys`, `user_base_urls`, `user_selected_models`, and `user_routing_rules`
  - inspect `run_agent_pipeline` to determine which kwargs it accepts
  - pass only accepted kwargs to `run_agent_pipeline`
- Result: the route now safely invokes the pipeline and avoids the signature mismatch.
- Recommended step: restart the backend process after this change so the updated code is active on `localhost:8000`.

---

## API walkthrough

```bash
# 1. Register
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@example.com","password":"SecurePass123!"}'

# 2. Login
curl -X POST localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com","password":"SecurePass123!"}'
# → { "access_token": "...", "refresh_token": "..." }

# 3. Chat — auto-routed across providers
curl -X POST localhost:8000/api/v1/llm/complete \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
        "messages": [{"role": "user", "content": "Explain CAP theorem in 3 sentences."}],
        "routing_strategy": "auto"
      }'
```

`routing_strategy` accepts `auto | cost | latency | quality | manual`.

## Architecture: the agent pipeline

```
security_agent  → scans every message for prompt injection / PII, masks & blocks
router_agent    → scores provider × model on quality/cost/latency, picks best fit
token_agent     → compresses history when approaching context-window limit
memory_agent    → (optional) pulls relevant chunks from ChromaDB for RAG
executor_agent  → calls the selected provider, retries with fallback on failure
post_process    → assembles response, logs metrics, persists conversation
```

Implemented as a LangGraph `StateGraph` in `backend/agents/graph.py` — security acts
as a conditional gate (`blocked → END`), and the executor falls back to a secondary
provider automatically if the primary fails.

## Project structure

```
llmops-gateway-ai/
├── backend/
│   ├── agents/            LangGraph multi-agent pipeline implementation
│   │   └── graph.py       security, routing, token optimization, memory, executor, evaluator
│   ├── api/               FastAPI endpoint modules and router configuration
│   │   ├── routes/        route handlers for auth, LLM, analytics, keys, memory, providers, health
│   │   └── __init__.py
│   ├── config.py          application settings and environment loading
│   ├── database/          SQLAlchemy async session and DB initialization
│   ├── main.py            FastAPI app entrypoint and route registration
│   ├── memory/            Redis caching and ChromaDB vector memory persistence
│   ├── models/            ORM models, Pydantic schemas, and DB entities
│   ├── observability/     Prometheus metrics export and instrumentation helpers
│   ├── router/            provider client registry, fallback routing, token/cost utilities
│   ├── security/          JWT auth, encryption, prompt scanning, API key resolution
│   └── utils/             shared helper utilities
├── frontend/              React + Vite admin console
│   ├── public/            static assets served by Vite
│   ├── src/               React app source
│   │   ├── components/    UI components for login, request stream, provider settings, diagrams
│   │   ├── lib/           client-side API helpers and demo data
│   │   ├── App.jsx        main application shell
│   │   ├── main.jsx       Vite entrypoint
│   │   └── index.css      global styles
│   ├── package.json       frontend dependencies and scripts
│   └── vite.config.js     dev server proxy and build configuration
├── infrastructure/        deployment and environment infrastructure
│   ├── docker/            Docker Compose and Nginx init scripts
│   ├── kubernetes/        manifests for deployment, service, ingress, HPA, PDB
│   └── terraform/         AWS infrastructure definitions for EKS, RDS, ElastiCache, ECR
├── monitoring/            observability configuration
│   ├── grafana/           dashboards and provisioning definitions
│   └── prometheus/        scrape config and alerting rules
├── migrations/            Alembic DB migrations
├── tests/                 unit and integration tests
└── .github/               CI/CD workflows and automation
```

### What each folder does

- `backend/`
  - Hosts the API server, multi-agent pipeline, provider routing, database models, and security layers.
  - The backend takes chat requests, routes them through security, selects a provider/model, calls the chosen LLM, records metrics, and persists request history.
- `backend/agents/`
  - Contains the LangGraph pipeline definition in `graph.py`.
  - The pipeline runs a chain of agents: security scanning, routing, token optimization, optional memory/RAG, LLM execution, evaluation/post-processing.
- `backend/api/routes/`
  - Defines REST endpoints used by the frontend and external clients.
  - Includes authentication, LLM completion, provider metadata, user key management, analytics, and health checks.
- `backend/router/`
  - Manages provider client selection and request cost/token utilities.
  - Includes logic for provider fallback when a user or server key is unavailable.
- `backend/memory/`
  - Implements response caching in Redis and semantic memory storage in ChromaDB.
  - Helps support conversational history and retrieval-augmented generation.
- `backend/security/`
  - Handles JWT auth, encrypted API keys, prompt/PII scanning, and user provider settings.
- `frontend/`
  - React + Tailwind UI for the operations console.
  - Communicates with backend APIs under `/api/v1` and displays live request stream, provider selection, and analytics.
- `infrastructure/`
  - Contains deployment artifacts for Docker, Kubernetes, and Terraform-driven AWS infrastructure.
- `monitoring/`
  - Prometheus and Grafana configuration files for observability and alerting.
- `migrations/`
  - Alembic migrations for evolving the PostgreSQL schema.
- `tests/`
  - End-to-end and unit tests that verify backend behavior, API routes, and integration flows.

## Testing

```bash
make test          # pytest with coverage
make lint          # ruff + mypy
make format        # black + ruff --fix
```

## Deployment

```bash
# AWS infra
make terraform-init && make terraform-plan && make terraform-apply

# Kubernetes
make k8s-deploy
make k8s-status
```

CI/CD (`.github/workflows/deploy.yml`) runs automatically on push to `main`:
lint → test → Trivy security scan → build & push to ECR → deploy to EKS → smoke test
→ automatic rollback on failure.

## Cost & security model

- **Cost tracking**: every request logs token counts + USD cost per provider/model;
  `/api/v1/analytics/cost-forecast` projects end-of-month spend and warns before
  budget overrun.
- **Security agent**: regex-based prompt-injection detection, PII masking (email,
  phone, SSN, credit card, AWS keys), risk-scored 0–1, blocks requests above 0.4.
- **API keys**: encrypted at rest with Fernet before being stored in Postgres.

## License

MIT — use freely for portfolios, interviews, and learning.
