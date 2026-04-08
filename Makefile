.PHONY: dev fe be db stop dev

$(shell [ -f .env ] || cp .env.example .env)
-include .env
export

db:
	docker compose up postgres -d

be: db
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload

fe:
	cd frontend && npm run dev

dev: db
	cd frontend && npm run dev &
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload

stop:
	docker compose down
