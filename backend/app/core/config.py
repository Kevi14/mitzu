from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://mitzu:mitzu@localhost:5432/mitzu"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://mitzu:mitzu@localhost:5432/mitzu"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_NAME: str = "mitzu_session"

    class Config:
        env_file = ".env"


settings = Settings()
