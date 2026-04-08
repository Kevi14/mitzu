# Stage 1 — Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2 — Python backend + static files
FROM python:3.13-slim AS backend

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy backend source first, then install deps
# (keeps .venv inside the container — never overwritten by host files)
COPY backend/ .

RUN uv sync --frozen --no-dev

# Copy frontend build output
COPY --from=frontend-builder /app/frontend/dist ./static

EXPOSE 8001

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
