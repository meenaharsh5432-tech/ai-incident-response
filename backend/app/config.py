from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://incident_user:incident_pass@localhost:5432/incident_db"
    REDIS_URL: str = "redis://localhost:6379"
    GROQ_API_KEY: str = ""
    GROQ_TIMEOUT: int = 30
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD: float = 0.85
    DIAGNOSIS_COOLDOWN_SECONDS: int = 3600
    DIAGNOSIS_SPIKE_MULTIPLIER: float = 10.0
    REQUIRE_API_KEY: bool = False  # set True in production to enforce X-API-Key on /api/errors
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
        "https://ai-incident-response-eight.vercel.app",
        "https://*.vercel.app",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
