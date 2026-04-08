"""
Tests for auth utilities and auth API routes.

- JWT creation / verification: pure unit tests, no DB
- Login / logout / me routes: use auth_client fixture (real auth logic, mocked DB)
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth.password import hash_password
from app.auth.utils import create_access_token, verify_token
from app.core.config import settings
from app.models.user import User


# ---------------------------------------------------------------------------
# JWT utility tests
# ---------------------------------------------------------------------------

def test_create_access_token_contains_sub():
    token = create_access_token("alice")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "alice"


def test_create_access_token_has_expiry():
    token = create_access_token("alice")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert "exp" in payload
    # Expiry should be ~ACCESS_TOKEN_EXPIRE_MINUTES from now
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert exp > datetime.now(timezone.utc)


def test_verify_token_valid():
    token = create_access_token("bob")
    assert verify_token(token) == "bob"


def test_verify_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc:
        verify_token("not.a.jwt")
    assert exc.value.status_code == 401


def test_verify_token_expired_raises_401():
    expired_token = jwt.encode(
        {"sub": "carol", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        verify_token(expired_token)
    assert exc.value.status_code == 401


def test_verify_token_missing_sub_raises_401():
    # Token with no 'sub' claim
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Auth API route tests
# ---------------------------------------------------------------------------

def _mock_user_result(db_mock, user: User | None):
    """Wire mock_db.execute to return a result whose scalar_one_or_none = user."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock.execute.return_value = mock_result


def test_login_success(auth_client):
    user = User(username="admin", hashed_password=hash_password("mitzu2024"))
    _mock_user_result(auth_client.mock_db, user)

    resp = auth_client.post("/api/auth/login", json={"username": "admin", "password": "mitzu2024"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged in"
    # Cookie should be set
    assert settings.COOKIE_NAME in resp.cookies


def test_login_wrong_password(auth_client):
    user = User(username="admin", hashed_password=hash_password("correct_password"))
    _mock_user_result(auth_client.mock_db, user)

    resp = auth_client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(auth_client):
    _mock_user_result(auth_client.mock_db, None)

    resp = auth_client.post("/api/auth/login", json={"username": "ghost", "password": "any"})
    assert resp.status_code == 401


def test_logout_clears_cookie(auth_client):
    # First log in to get a valid session cookie
    user = User(username="admin", hashed_password=hash_password("mitzu2024"))
    _mock_user_result(auth_client.mock_db, user)
    login = auth_client.post("/api/auth/login", json={"username": "admin", "password": "mitzu2024"})
    assert login.status_code == 200

    resp = auth_client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out"


def test_me_returns_username(auth_client):
    # Log in first
    user = User(username="admin", hashed_password=hash_password("mitzu2024"))
    _mock_user_result(auth_client.mock_db, user)
    auth_client.post("/api/auth/login", json={"username": "admin", "password": "mitzu2024"})

    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_me_without_cookie_returns_401(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 401
