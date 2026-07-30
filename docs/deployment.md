# Vectoria Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- 8GB+ RAM (for sentence-transformer + FAISS)

### Setup
```bash
# Clone and install
git clone https://github.com/chintan1529/vectoria-semantic-search.git
cd vectoria-semantic-search
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Configure
cp .env.example .env
# Edit .env with your API keys

# Build the vector index
python build_index.py

# Start
python -m uvicorn backend.api:app --port 8000  # Backend
cd frontend && npm run dev                       # Frontend
```

---

## Docker Deployment (Recommended)

### Quick Start
```bash
docker compose up --build
```

This starts the full platform:
- **Backend API**: `http://localhost:8000`
- **Frontend UI**: `http://localhost:3000`
- **Health Check**: `http://localhost:8000/api/health`

### Persistent Data
Docker Compose configures three persistent volumes:
| Volume | Path | Purpose |
|---|---|---|
| `vectoria-storage` | `/app/storage` | FAISS index, chunks, embeddings |
| `vectoria-logs` | `/app/logs` | Application logs |
| `vectoria-data` | `/app/data` | Evaluation datasets and reports |

### Environment Variables
Set in `.env` (automatically loaded by Docker Compose):

| Variable | Required | Description |
|---|---|---|
| `VECTORIA_CHAT_PROVIDER` | ❌ | Primary Chat LLM Provider (default: `gemini`) |
| `VECTORIA_RESEARCH_PROVIDER` | ❌ | Research LLM Provider (default: `gemini`) |
| `VECTORIA_FALLBACK_PROVIDER` | ❌ | Fallback Provider (default: `huggingface`) |
| `VECTORIA_GEMINI_API_KEY` | ✅ | Gemini API key |
| `VECTORIA_HF_API_KEY` | ✅ | HuggingFace API key |
| `VECTORIA_OPENAI_API_KEY` | ❌ | OpenAI API key |
| `VECTORIA_TOP_K_DEFAULT` | ❌ | Retrieval depth (default: `5`) |
| `VECTORIA_MAX_CONTEXT_TOKENS` | ❌ | Context window (default: `4000`) |
| `VECTORIA_ALLOWED_ORIGINS` | ❌ | CORS origins (default: `localhost`) |

---

## Cloud Deployment

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Set environment variables in the Railway dashboard.

### Render
1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect your GitHub repository
3. Set **Build Command**: `docker compose build`
4. Set **Start Command**: `docker compose up`
5. Add environment variables in the Render dashboard

### Fly.io
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly launch
fly deploy
fly secrets set VECTORIA_LLM_API_KEY=your-key
fly secrets set VECTORIA_HF_API_KEY=your-key
```

### VPS (Ubuntu)
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone and deploy
git clone https://github.com/chintan1529/vectoria-semantic-search.git
cd vectoria-semantic-search
cp .env.example .env
# Edit .env with your API keys

docker compose up -d --build
```

---

## Health Monitoring

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Backend health status |
| `/api/ready` | GET | Readiness probe |
| `/api/status` | GET | Full system status |
| `/api/routes` | GET | Registered routes |

The Docker container includes a built-in health check that polls `/api/health` every 30 seconds.

---

## Production Checklist

- [ ] Rotate API keys (never use development keys in production)
- [ ] Set `VECTORIA_ALLOWED_ORIGINS` to your production domain
- [ ] Ensure `storage/` directory contains the pre-built FAISS index
- [ ] Configure persistent storage volumes
- [ ] Set up log rotation (logs can grow large under heavy use)
- [ ] Monitor `/api/health` with your alerting system
- [ ] Review the [Platform Audit](platform_audit.md) for known risks
