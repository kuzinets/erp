from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://erp_admin:erp_secret_2026@db:5432/erp_db"
    DATABASE_URL_SYNC: str = "postgresql://erp_admin:erp_secret_2026@db:5432/erp_db"
    JWT_SECRET: str = "library-jwt-secret-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480
    LIBRARY_BASE_URL: str = "http://host.docker.internal:8000"
    CORS_ORIGINS: list[str] = ["http://localhost:3001", "http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
