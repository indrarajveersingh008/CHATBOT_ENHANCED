import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek/deepseek-chat-v3-0324")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))

    # Models that can analyze uploaded images (vision/multimodal)
    VISION_CAPABLE_MODELS: frozenset[str] = frozenset({
        "google/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
    })
    DEFAULT_VISION_MODEL: str = os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.5-flash")

    # SQLite by default so the project runs with zero extra setup.
    # Set DATABASE_URL on Render/production to point at Postgres instead.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_nexus.db")

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # Comma-separated list of allowed origins, e.g. "https://myapp.vercel.app,http://localhost:5500"
    _raw_origins: str = os.getenv("CORS_ORIGINS", "*")
    CORS_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",")] if _raw_origins else ["*"]


settings = Settings()

if not settings.OPENROUTER_API_KEY:
    print("⚠️  WARNING: OPENROUTER_API_KEY is not set. /chat will fail until it is.")
