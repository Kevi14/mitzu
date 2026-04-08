.PHONY: dev fe be db stop dev

DB_URL=postgresql+asyncpg://mitzu:mitzu@localhost:5432/mitzu
SYNC_DB_URL=postgresql+psycopg2://mitzu:mitzu@localhost:5432/mitzu
SECRET_KEY=dev-secret-change-in-prod

db:
	docker compose up postgres -d

be: db
	cd backend && \
	DATABASE_URL=$(DB_URL) \
	SYNC_DATABASE_URL=$(SYNC_DB_URL) \
	SECRET_KEY=$(SECRET_KEY) \
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

fe:
	cd frontend && npm run dev

dev: db
	cd frontend && npm run dev &
	cd backend && \
	DATABASE_URL=$(DB_URL) \
	SYNC_DATABASE_URL=$(SYNC_DB_URL) \
	SECRET_KEY=$(SECRET_KEY) \
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

stop:
	docker compose down
