# Mitzu — NYC Taxi Analytics Dashboard

A data analytics dashboard built on the [NYC TLC Yellow Taxi dataset](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

The core feature is a **React Flow pipeline canvas** where you chain analytics nodes (DataSource → Filter → Aggregation → Visualization) and execute the whole graph in one click. The server resolves the node graph via topological sort and pushes filters down into SQL before executing queries against Postgres.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), Pandas, PyArrow |
| Database | PostgreSQL 16 |
| Auth | JWT in `httpOnly` cookie (HS256 via python-jose) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Pipeline UI | @xyflow/react (React Flow) |
| Charts | Recharts + @nivo/heatmap |
| Infra | Docker Compose (local), Terraform (AWS), Helm (K3s) |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- No other local dependencies required — everything runs in containers

For local frontend development (optional):
- Node.js 20+
- Python 3.12 + [uv](https://docs.astral.sh/uv/getting-started/installation/)

---

## Quick Start

```bash
git clone <repo-url> && cd mitzu
docker compose up --build
```

The app is available at **http://localhost:8000**

Login: `admin` / `mitzu2024`

---

## Ingest Data

Before running a pipeline you need to ingest at least one month of data.

**Via the dashboard UI:** Use the year/month selectors in the top bar and click **Ingest**.

**Via curl:**
```bash
# Login (cookie saved to cookies.txt)
curl -c cookies.txt -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"mitzu2024"}'

# Ingest January 2024 (~3M rows, takes ~1-2 min)
curl -b cookies.txt -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"year":2024,"month":1}'
```

---

## Build a Pipeline

1. **Drag** a **Data Source** node from the left palette onto the canvas
2. **Configure** year/month in the right panel (click the node to select it)
3. **Drag** an **Aggregation** node (e.g. "Trips by Hour") and connect it
4. **Drag** a **Visualization** node, connect it, choose chart type + keys
5. Click **▶ Execute Pipeline**

### Available Analytics

| Node type | What it shows |
|---|---|
| Trips by Hour | Trip count distribution across 24 hours |
| Fare vs Distance | Scatter of fare vs miles with IQR outlier highlighting |
| Top Pickup Zones | Top 20 pickup locations by volume |
| Tip Rate by Payment | Average tip % for credit card vs cash |
| Revenue Heatmap | Total revenue by day-of-week × hour |
| Avg Speed by Hour | Traffic speed proxy (miles/hour) across the day |
| Congestion Trend | Monthly average congestion surcharge over time |
| Anomaly Flags | Counts of zero-distance, negative fare, sub-1min trips |

---

## Local Frontend Development

```bash
# Start Postgres and backend
docker compose up postgres backend

# Run frontend dev server (hot reload)
cd frontend && npm install && npm run dev
# → http://localhost:5173 (proxies /api to localhost:8000)
```

```bash
# Backend only (no Docker)
cd backend
uv sync
DATABASE_URL=postgresql+asyncpg://mitzu:mitzu@localhost:5432/mitzu \
SYNC_DATABASE_URL=postgresql+psycopg2://mitzu:mitzu@localhost:5432/mitzu \
SECRET_KEY=dev uv run uvicorn app.main:app --reload
```

---

## Linting & Formatting

```bash
# Backend
cd backend
uv run ruff check .
uv run ruff format .

# Frontend
cd frontend
npm run lint
npm run format
```

---

## Project Layout

```
mitzu/
├── backend/          # FastAPI app (auth, ingest, analytics, health)
├── frontend/         # React + React Flow SPA
├── infra/
│   ├── terraform/    # AWS deployment (ECS Fargate + RDS + ALB)
│   └── helm/         # K3s self-hosted chart
├── prompts/          # AI collaboration log (init_prompt, spec, iterations)
└── docs/             # deployment, architecture, learnings
```

---

## Deployment

See [`docs/deployment.md`](docs/deployment.md) for the full AWS architecture plan and `infra/terraform/` for the Terraform modules. No actual deployment is required — the app is designed to run fully locally via Docker Compose.
