import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.auth.password import hash_password
from app.auth.router import router as auth_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.zones import router as zones_router
from app.core.config import settings
from app.core.db import AsyncSessionLocal, Base, engine
from app.models import User  # noqa: F401 — registers all models with Base
from app.models import IngestionLog, TaxiZone, Trip  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admin user and zones
    async with AsyncSessionLocal() as session:
        from app.services.zone_seeder import seed_zones
        from sqlalchemy import text as _text

        # Reset stale pending ingestions left over from a previous container run
        await session.execute(
            _text("UPDATE ingestion_log SET status='error', error_msg='interrupted by restart' WHERE status='pending'")
        )
        await session.commit()

        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            session.add(User(username="admin", hashed_password=hash_password("mitzu2024")))
            await session.commit()

        await seed_zones(session)

    yield


app = FastAPI(title="Mitzu API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(zones_router)

app.include_router(ingest_router)
app.include_router(analytics_router)

# Static files must be mounted last (after all API routes)
import os
from starlette.types import Receive, Scope, Send


class SPAStaticFiles(StaticFiles):
    """StaticFiles that handles SPA routing and ignores non-HTTP scopes."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        await super().__call__(scope, receive, send)

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except Exception:
            # Fall back to index.html for SPA client-side routes
            return await super().get_response("index.html", scope)


if os.path.isdir("static"):
    app.mount("/", SPAStaticFiles(directory="static", html=True), name="static")
