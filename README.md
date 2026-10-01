# eRTMAC-NWIS MVP

eRTMAC-NWIS (Nearby Wells Intelligence System) is an AI-powered offset-well knowledge and decision-support platform for drilling operations. It is being developed for SIH 2026 Problem Statement 121 / SIH26121, Oil India Limited.

## Current Development Phase

Phase 7: FastAPI Intelligence Orchestration (COMPLETE). Phases 1–7 complete.

## Deployment with Docker

The repository includes a production-oriented Docker Compose setup for the React frontend, FastAPI backend, PostgreSQL, PostGIS, and pgvector. The frontend serves the application and proxies `/api`, `/health`, and `/ws` to the backend, so a single public port is exposed.

1. Copy `.env.example` to `.env` and set a strong `POSTGRES_PASSWORD`. Add optional LLM keys only if grounded generation is needed.
2. Run `docker compose up --build -d` from this directory. The one-time `initialize` service loads the synthetic dataset and trains the included risk model after the database is ready.
3. Wait for initialization to finish with `docker compose logs -f initialize`, then open `http://localhost` (or the host and `APP_PORT` you configured).

For an internet-facing deployment, place TLS termination (for example, a managed load balancer or reverse proxy) in front of port 80, set `FRONTEND_URL` to the public HTTPS origin, and keep `.env` outside source control. Database data persists in the named `postgres_data` volume.

### Local Requirements

- Python 3.x
- PostgreSQL running on `localhost:5432`
- PostGIS and pgvector enabled in the `nwis` database
- Node.js for the deferred frontend phase

## Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Set the local PostgreSQL password in `backend/.env`. Never commit that file.

Backend: http://localhost:8000  
Swagger: http://localhost:8000/docs

Endpoints currently implemented:

- `GET /` returns the API status message.
- `GET /health` returns the service health.
- `GET /db-test` executes `SELECT 1` against PostgreSQL.
- `GET /api/wells` returns the list of all available wells with metadata.
- `GET /api/wells/{well_id}` returns detailed well info including formations, recent drilling logs, and historical events.
- `GET /api/wells/{well_id}/similar` returns nearby similar offset wells.
- `POST /api/wells/{well_id}/risk` validates well existence and returns XGBoost drilling-risk class probabilities for given parameters.
- `GET /api/wells/{well_id}/intelligence` unified orchestration endpoint combining well metadata, formations, recent logs, events, similar wells, ML risk prediction, and native pgvector RAG context.
- `GET /api/similarity/{well_id}` returns nearby similar wells.
- `POST /api/risk/predict` returns XGBoost drilling-risk class probabilities.
- `POST /api/rag/query` retrieves historical report chunks using native pgvector and optionally generates a grounded answer.

When `DATABASE_URL` is configured, startup creates the `wells`, `formations`, `drilling_logs`, `events`, and `rag_documents` tables.

## Well Similarity Engine

The NWIS MVP uses PostGIS to identify nearby historical wells and then applies a deterministic weighted similarity algorithm. Candidate wells are filtered using a configurable radius, and the final score combines:

- Geographic distance: 40%
- Formation overlap: 30%
- Total depth similarity: 20%
- Geological similarity: 10%

The engine is intentionally not an ML/AI similarity model. It is a simple explainable scoring system built from spatial filtering plus historical well comparisons.

### API

- `GET /api/similarity/{well_id}`
- Optional query parameters: `radius_km` and `limit`

Example:

```http
GET /api/similarity/W001?radius_km=10&limit=5
```

## Drilling Risk Model

A group-aware XGBoost classifier predicts `event_label` from seven numeric drilling features. Training and inference live under `ml/`. The FastAPI route does not train; it loads `ml/models/risk_model.joblib` once.

Train:

```powershell
cd nwis-mvp
$env:PYTHONPATH = "$PWD;$PWD\backend"
.\backend\.venv\Scripts\python.exe -m ml.training.train_risk_model
```

### API

```http
POST /api/risk/predict
```

The dataset is synthetic. This model is not production-ready and is not validated on real OIL drilling data.

## RAG System

Phase 6 adds retrieval-augmented generation for historical drilling questions using **PostgreSQL + pgvector**.

The PDFs in `rag/documents/` are **synthetic development data** generated from the local NWIS database. They are **not** real OIL drilling reports.

Pipeline:

1. Generate synthetic well PDFs from `wells`, `formations`, `drilling_logs`, and `events`
2. Extract text with PyMuPDF
3. Split into deterministic word chunks (~650 words, overlap 80)
4. Embed with `sentence-transformers/all-MiniLM-L6-v2` (dimension: 384)
5. Store chunks and native vectors in PostgreSQL table `rag_documents` (`vector(384)`)
6. Embed user question into 384-dimensional vector and retrieve top similar chunks directly in PostgreSQL using pgvector cosine distance (`<=>`)
7. Generate an answer only from retrieved evidence (LLM is optional)

Vector store: **PostgreSQL 18.3 + pgvector 0.8.6**.
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension:** 384
- **Similarity:** cosine distance executed natively inside PostgreSQL
- **Operator:** `<=>` (converted to similarity via `1 - cosine_distance`)

Default retrieval: `top_k=5`, minimum cosine similarity `0.10`. This was calibrated against the current short synthetic report chunks: relevant W005 queries score around `0.126`, while an unrelated cake query scores below `0.07`. Below the threshold the API returns no sources and does not call an LLM.

```http
POST /api/rag/query
{
  "question": "What problems occurred in W005?",
  "top_k": 5
}
```

Generation uses `LLM_PROVIDER`, `OPENAI_API_KEY`, and `LLM_MODEL` from `backend/.env`. Ingestion and retrieval work without a key. The API does not invent LLM answers when no key is configured.

See `rag/README.md` for generate/ingest commands.

## Deferred phases

WebSockets, frontend integration, maps, Docker, and deployment are intentionally not part of Phase 6.
