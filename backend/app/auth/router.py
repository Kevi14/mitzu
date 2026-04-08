from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import verify_password
from app.auth.utils import create_access_token, get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.username)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return {"message": "Logged in"}


@router.post("/logout")
async def logout(response: Response, _: str = Depends(get_current_user)):
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(username: str = Depends(get_current_user)):
    return {"username": username}
