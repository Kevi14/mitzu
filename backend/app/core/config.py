from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://mitzu:mitzu@localhost:5432/mitzu"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://mitzu:mitzu@localhost:5432/mitzu"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_NAME: str = "mitzu_session"
    BACKEND_PORT: int = 8001
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        # Backend is run from the `backend/` directory; ../.env is the project root.
        env_file = "../.env"
        extra = "ignore"


settings = Settings()
