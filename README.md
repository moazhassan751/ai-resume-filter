# TalentLens AI (AI Resume Filter)

An AI-powered resume intelligence platform with a FastAPI backend and a Next.js frontend. It classifies resumes, computes ATS-style scores, performs semantic search with ChromaDB, and provides recruiter analytics dashboards. Optional CrewAI agents and Gemini-powered RAG add multi-agent reasoning and ranking.

## Highlights

- FastAPI backend with JWT auth, rate limiting, and security middleware
- Next.js frontend with analytics, uploads, and explainability panels
- Semantic search via sentence-transformer embeddings + ChromaDB
- OCR-aware resume parsing for PDF, DOCX, and image resumes
- ATS scoring and ranking with explainable signals
- Multi-agent analysis (CrewAI) with safe fallbacks
- Async model training with Celery + Redis
- Observability hooks: Prometheus, Grafana, optional Sentry + OpenTelemetry

## Architecture

- Backend: FastAPI (`ai_resume_filter/app`)
- Frontend: Next.js (`frontend`)
- Vector store: ChromaDB (local persistent directory)
- Persistence: MongoDB (users, metrics, history), optional Postgres
- Background jobs: Celery workers with Redis broker
- Monitoring: Prometheus + Grafana

## Quick Start (Local)

### 1) Backend (FastAPI)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r ai_resume_filter/requirements.txt
copy ai_resume_filter\.env.example .env

# Start the API
cd ai_resume_filter
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2) Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open:
- API: http://127.0.0.1:8000
- Frontend: http://localhost:3000

## Docker (Dev and Prod)

This repo ships a multi-service Compose stack with `dev` and `prod` profiles.

### Development profile

```bash
docker compose --profile dev up --build
```

Services:
- `backend-dev` (FastAPI with reload)
- `frontend-dev` (Next.js dev)
- `worker-dev` (Celery worker)
- `mongo`, `redis`

### Production profile

```bash
copy .env.production.example .env.production
# edit .env.production with secrets

docker compose --profile prod --env-file .env.production up --build
```

Services:
- `backend` (Gunicorn + Uvicorn workers)
- `frontend` (Next.js production build)
- `worker` (Celery)
- `mongo`, `redis`, `postgres`
- `prometheus`, `grafana`, `celery-exporter`, `flower`

## API Overview

Base URL: `/api/v1`

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/token`

### Data + Uploads
- `GET /api/v1/data/status`
- `GET /api/v1/data/datasets`
- `GET /api/v1/data/statistics`
- `POST /api/v1/data/upload`
- `POST /api/v1/data/intelligence`
- `POST /api/v1/data/ats/score`
- `GET /api/v1/data/history`

### Search + RAG
- `POST /api/v1/search/semantic`
- `POST /api/v1/rag/analyze`

### Ranking
- `POST /api/v1/ranking/rank-candidates`

### Analytics + Explainability
- `GET /api/v1/analytics/dashboard`
- `GET /api/v1/analytics/recruiter-insights`
- `POST /api/v1/analytics/explain`

### Model + Training
- `GET /api/v1/model/load`
- `POST /api/v1/model/predict`
- `POST /api/v1/model/train-async`
- `GET /api/v1/model/train-status/{task_id}`
- `GET /api/v1/model/report`
- `GET /api/v1/model/metrics`
- `POST /api/v1/model/metrics`

### Health and Metrics
- `GET /health`
- `GET /live`
- `GET /ready`
- `GET /metrics`

## Data Pipeline and Scripts

The project includes dataset utilities and normalization scripts:

```bash
python ai_resume_filter/scripts/inventory_datasets.py
python ai_resume_filter/scripts/normalize_datasets.py
python ai_resume_filter/scripts/data_pipeline.py
python ai_resume_filter/scripts/train_model.py
python ai_resume_filter/scripts/index_embeddings.py
```

`services/data_service.py` loads multiple datasets at startup, including:
- `resume_data.csv`
- `Resume/Resume.csv`
- `resumes_dataset.jsonl`
- CareerCorpus (Excel)
- Resume PDFs by category
- Optional HuggingFace dataset (`ahmedheakl/resume-atlas`)

Set `SKIP_HF_DATASET=1` to avoid pulling HF datasets.

## Environment Variables

See the templates:
- `ai_resume_filter/.env.example` (local)
- `.env.production.example` (production)

Key variables:
- `SECRET_KEY` (required in production)
- `MONGODB_URL`, `MONGODB_DB`
- `CHROMA_PERSIST_DIRECTORY`
- `MODEL_PATH`, `VECTORIZER_PATH`
- `UPLOAD_DIR`, `EXPORT_DIR`, `CACHE_DIR`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- `CREWAI_PROVIDER`, `CREWAI_MODEL`, `CREWAI_TASK_TIMEOUT`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

## Testing

```bash
cd ai_resume_filter
pytest
```

CI sets `CREWAI_MOCK_MODE=1` and `EMBEDDING_MOCK_MODE=1` to avoid model downloads.

## Monitoring

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin/admin by default)
- Flower (Celery UI): `http://localhost:5555`

## Security Notes

See [docs/SECURITY.md](docs/SECURITY.md) and [docs/SECRETS.md](docs/SECRETS.md) for hardening guidance, secret rotation, and recommended production controls.

## License

MIT License
