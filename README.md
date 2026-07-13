# 🤖 LLMOps Gateway AI

> Intelligent Multi-LLM Routing, Token Optimization & Cost Management Platform

A production-ready AI Gateway that intelligently routes requests across multiple Large Language Models (LLMs) based on **quality, latency, cost, and user-defined routing rules**.

Built using **FastAPI, LangGraph, React, PostgreSQL, Redis, ChromaDB, Docker, Kubernetes, and AWS** to demonstrate production-grade AI Engineering, MLOps, Observability, and Cloud Deployment.

---

# 🚀 Features

- Multi-LLM intelligent routing
- LangGraph Multi-Agent Architecture
- Prompt Injection Detection
- PII Detection & Masking
- Automatic Provider Failover
- Token Optimization
- Conversation Memory (RAG)
- Cost Tracking
- Request Analytics
- Live Dashboard
- Docker Deployment
- Kubernetes Ready
- AWS Infrastructure (Terraform)
- GitHub Actions CI/CD
- Production Monitoring with Prometheus & Grafana

---

# 🏗 Architecture

```
                 ┌────────────────────────────┐
                 │      React Dashboard       │
                 └────────────┬───────────────┘
                              │
                              ▼
                 ┌────────────────────────────┐
                 │      FastAPI Gateway       │
                 └────────────┬───────────────┘
                              │
                              ▼
      ┌────────────────────────────────────────────┐
      │      LangGraph Multi-Agent Pipeline        │
      │                                            │
      │  Security Agent                            │
      │          ↓                                 │
      │  Router Agent                              │
      │          ↓                                 │
      │  Token Optimization                        │
      │          ↓                                 │
      │  Memory (RAG)                              │
      │          ↓                                 │
      │  LLM Executor                              │
      │          ↓                                 │
      │  Response Evaluator                        │
      └────────────────────────────────────────────┘
                              │
          ┌──────────┬─────────┴──────────┬─────────┐
          ▼          ▼                    ▼         ▼
      OpenAI     Anthropic            Gemini    Mistral
                              │
                              ▼
          PostgreSQL • Redis • ChromaDB
                              │
                              ▼
           Prometheus • Grafana Monitoring
```

---

# ⚡ Tech Stack

## Backend

- FastAPI
- Python
- SQLAlchemy (Async)
- PostgreSQL
- Redis
- ChromaDB
- JWT Authentication
- LangGraph
- Pydantic

## Frontend

- React
- Tailwind CSS
- Axios
- Lucide Icons
- Vite

## AI

- OpenAI
- Google Gemini
- Anthropic Claude
- Mistral
- Multi-Agent Architecture
- Retrieval-Augmented Generation (RAG)

## DevOps

- Docker
- Docker Compose
- Kubernetes
- Terraform
- AWS EKS
- AWS RDS
- AWS ECR
- AWS ElastiCache

## Monitoring

- Prometheus
- Grafana
- Structured Logging

---

# 🧠 Multi-Agent Pipeline

The project uses **LangGraph StateGraph** to coordinate multiple AI agents.

| Agent | Responsibility |
|---------|----------------|
| Security Agent | Prompt Injection Detection & PII Masking |
| Router Agent | Intelligent Provider Selection |
| Token Agent | Prompt Compression |
| Memory Agent | RAG using ChromaDB |
| Executor Agent | Calls selected LLM |
| Evaluator Agent | Scores model response |
| Post Processing | Logging & Response Formatting |

---

# 🔒 Security

- Prompt Injection Detection
- PII Detection
- Encrypted API Keys
- JWT Authentication
- Rate Limiting
- Request Validation
- Automatic Request Blocking

---

# 📊 Dashboard Features

- Live Request Stream
- Cost Analytics
- Token Analytics
- Provider Usage
- Pipeline Visualization
- Provider Health
- Security Alerts
- Request History

---

# 📁 Project Structure

```
llmops-gateway-ai
│
├── backend
│   ├── agents
│   ├── api
│   ├── database
│   ├── memory
│   ├── models
│   ├── observability
│   ├── router
│   ├── security
│   └── utils
│
├── frontend
│
├── infrastructure
│   ├── docker
│   ├── kubernetes
│   └── terraform
│
├── monitoring
│
├── migrations
│
├── tests
│
└── .github
```

---

# ⚙ Environment Setup

Copy the example environment file.

```bash
cp .env.example .env
```

Update the following values inside `.env`.

```
GEMINI_API_KEY=your_api_key
OPENAI_API_KEY=your_api_key
ANTHROPIC_API_KEY=your_api_key
DATABASE_URL=...
REDIS_URL=...
```

---

# 🐳 Docker

```bash
docker compose up --build
```

---

# 💻 Local Development

Install dependencies

```bash
pip install -r requirements.txt
```

Start backend

```bash
uvicorn backend.main:app --reload
```

Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# ☸ Kubernetes

Deploy

```bash
make k8s-deploy
```

Check

```bash
make k8s-status
```

---

# ☁ AWS Deployment

Terraform

```bash
make terraform-init

make terraform-plan

make terraform-apply
```

---

# 📈 Monitoring

| Service | URL |
|----------|-----|
| FastAPI Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Frontend | http://localhost:3002 |

---

# 🧪 Testing

```bash
make test
```

Lint

```bash
make lint
```

Formatting

```bash
make format
```

---

# 🔄 CI/CD

GitHub Actions Pipeline

- Code Formatting
- Ruff
- MyPy
- Unit Tests
- Security Scan
- Docker Build
- Push to AWS ECR
- Kubernetes Deployment
- Smoke Tests
- Automatic Rollback

---

# 📌 Highlights

- Production-grade architecture
- Multi-LLM orchestration
- LangGraph agent workflow
- Cost-aware routing
- Cloud-native deployment
- Real-time observability
- Secure API key management
- AI Engineering portfolio project

---

# 📜 License

MIT License

---

# 👨‍💻 Author

**Ujjwal Kaushik**

B.Tech Artificial Intelligence & Machine Learning

AI Engineer | Machine Learning | MLOps | Generative AI
