import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "meta-llama/llama-3.3-70b-instruct:free")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))

    # Models that can analyze uploaded images (vision/multimodal)
    VISION_CAPABLE_MODELS: frozenset[str] = frozenset({
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "google/gemini-2.5-flash",
        "openai/gpt-4o-mini",
    })
    DEFAULT_VISION_MODEL: str = os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

    # SQLite by default so the project runs with zero extra setup.
    # Set DATABASE_URL on Render/production to point at Postgres instead.
    # We also check POSTGRES_URL, which is injected by Vercel/Supabase/Neon database integrations.
    _db_url: str = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "sqlite:///./ai_nexus.db"
    
    # SQLAlchemy 1.4+ deprecated postgres:// connection URLs. If it starts with postgres://,
    # convert it to postgresql:// so that SQLAlchemy can load the PostgreSQL driver correctly.
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    DATABASE_URL: str = _db_url

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # Comma-separated list of allowed origins, e.g. "https://myapp.vercel.app,http://localhost:5500"
    _raw_origins: str = os.getenv("CORS_ORIGINS", "*")
    CORS_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",")] if _raw_origins else ["*"]


settings = Settings()

if not settings.OPENROUTER_API_KEY:
    print("⚠️  WARNING: OPENROUTER_API_KEY is not set. /chat will fail until it is.")
