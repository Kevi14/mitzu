# Mitzu Backend

## Running Locally

### Prerequisites
- Python 3.13+
- PostgreSQL 16 (running locally on port 5432)
- [uv](https://github.com/astral-sh/uv) for dependency management

### Setup

1. Install dependencies:
```bash
cd backend
uv sync
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql+asyncpg://mitzu:mitzu@localhost:5432/mitzu"
export SYNC_DATABASE_URL="postgresql+psycopg2://mitzu:mitzu@localhost:5432/mitzu"
export SECRET_KEY="dev-secret"
```

3. Create the database (if it doesn't exist):
```bash
createdb mitzu -U mitzu
# or
psql -U postgres -c "CREATE USER mitzu WITH PASSWORD 'mitzu';"
psql -U postgres -c "CREATE DATABASE mitzu OWNER mitzu;"
```

4. Run the server:
```bash
uv run python -m app.main
```

The API will be available at http://localhost:8001

## API Documentation

Once running, visit http://localhost:8001/docs for the Swagger UI.