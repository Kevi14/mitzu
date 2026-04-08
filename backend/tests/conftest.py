"""
Shared fixtures for all tests.

API tests use `api_client` — a minimal FastAPI app (no lifespan, no real DB).
Auth-specific tests use `auth_client` — same but without the get_current_user override,
so the actual authentication logic is exercised.
"""
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.analytics import router as analytics_router
from app.api.routes.health import router as health_router
from app.api.routes.zones import router as zones_router
from app.auth.router import router as auth_router
from app.auth.utils import get_current_user
from app.core.db import get_db


@pytest.fixture
def mock_db():
    """Async SQLAlchemy session mock."""
    return AsyncMock()


@pytest.fixture
def api_client(mock_db):
    """
    TestClient with:
    - all route routers mounted
    - get_db overridden → AsyncMock
    - get_current_user overridden → 'admin'  (skips JWT checks)
    - no lifespan (no real DB needed)
    """
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(analytics_router)
    app.include_router(zones_router)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: "admin"
    with TestClient(app) as c:
        c.mock_db = mock_db  # type: ignore[attr-defined]
        yield c


@pytest.fixture
def auth_client(mock_db):
    """
    TestClient with get_db overridden but get_current_user intact.
    Use this when testing login / logout / JWT behaviour directly.
    """
    app = FastAPI()
    app.include_router(auth_router)
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        c.mock_db = mock_db  # type: ignore[attr-defined]
        yield c
