# Architecture

## Local (Docker Compose)

```
Browser
  │
  ▼
localhost:8000
  │
  ├── /api/*       → FastAPI routes (auth, ingest, pipeline, zones, health)
  └── /*           → React SPA (StaticFiles from dist/)
        │
        ▼
     PostgreSQL 16 (localhost:5432)
```

Single Docker image built from a multi-stage Dockerfile:
1. **Stage 1 (node:20-alpine)** — runs `npm run build`, outputs `dist/`
2. **Stage 2 (python:3.12-slim)** — installs Python deps via `uv`, copies `dist/` to `static/`

`docker compose up --build` starts Postgres + the backend. That's it.

---

## Production (AWS)

```
User Browser
     │  HTTPS
     ▼
[CloudFront (optional, for edge caching)]
     │
     ▼
[Application Load Balancer]
  HTTPS 443 → forward
  HTTP  80  → redirect to 443
     │
     ▼
[ECS Fargate — mitzu-backend container]
  ├── FastAPI handles /api/*
  ├── StaticFiles serves React SPA at /*
  └── Ingestion runs in run_in_executor (threadpool)
     │
     ▼
[RDS PostgreSQL 16 — private subnet]
  ├── trips table (~10-15M rows/month ingested)
  ├── taxi_zones lookup (265 rows, seeded on startup)
  ├── ingestion_log (idempotency tracker)
  └── users (admin only for now)
```

---

## Data Flow

### Ingestion
```
POST /api/ingest {year, month}
  → download Parquet from NYC TLC CloudFront URL (httpx async)
  → pd.read_parquet() → rename columns → drop nulls → add data_month
  → asyncio.run_in_executor → df.to_sql(chunksize=5000, if_exists='append')
  → update ingestion_log (idempotent: ON CONFLICT DO NOTHING on trips)
```

### Pipeline Execution
```
POST /api/pipeline/execute {nodes, edges}
  → analytics_executor.py
      1. Kahn's topological sort
      2. Traverse sorted nodes:
         DataSource  → store {year, month} params
         Filter      → append WHERE params to context
         Aggregation → call analytics/<type>.py::run(params, filters, db)
         Visualization → pass through data + attach chart config
  → return {results: {node_id: {data, metadata}}}
```

### Authentication
```
POST /api/auth/login {username, password}
  → bcrypt verify → create HS256 JWT
  → Set-Cookie: mitzu_session=<jwt>; HttpOnly; SameSite=Strict
  
All subsequent requests:
  → Cookie attached automatically (credentials: 'include')
  → FastAPI: request.cookies["mitzu_session"] → verify_token()
  
POST /api/auth/logout
  → Set-Cookie: mitzu_session=; Max-Age=0 (clears cookie)
```

---

## Backend Module Layout

```
app/
├── main.py              # FastAPI app + lifespan (seed admin, seed zones, create tables)
├── auth/                # login/logout/me routes + JWT utils + bcrypt
├── api/routes/          # ingest, analytics, zones, health
├── core/                # config (pydantic-settings) + db (async SQLAlchemy)
├── models/              # SQLAlchemy ORM: User, Trip, TaxiZone, IngestionLog
├── schemas/             # Pydantic: auth, ingest, analytics (pipeline in/out)
├── services/
│   ├── ingestion.py     # download + transform + bulk insert
│   ├── zone_seeder.py   # one-time CSV import
│   └── analytics_executor.py  # topo-sort + context propagation
└── analytics/           # 8 query files, each exposing run(params, filters, db)
```

## Frontend Module Layout

```
src/
├── api/          # fetch wrapper + auth/analytics API functions
├── components/
│   ├── flow/     # React Flow canvas + 4 custom node types + config panel
│   └── charts/   # BarChart, ScatterChart, LineChart, HeatmapChart (Recharts + Nivo)
├── pages/        # LoginPage, DashboardPage
├── store/        # pipelineStore (Zustand) — nodes, edges, execute, results
└── types/        # pipeline.ts — NodeData, AnalyticType, ChartType, etc.
```

---

## Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Frontend serving | FastAPI `StaticFiles` | Eliminates S3 + CloudFront module |
| JWT transport | `httpOnly` cookie | XSS-safe; cookie invisible to JS |
| DB partitioning | Single table + `data_month` index | Partition-ready schema; not needed at demo scale |
| Pipeline execution | Server-side topo-sort | Keeps analytics logic out of the browser |
| Ingestion threading | `run_in_executor` | pandas `to_sql` is sync; avoids blocking the event loop |
