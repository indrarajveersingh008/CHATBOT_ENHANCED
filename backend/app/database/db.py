from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from ..config.settings import settings

# SQLite needs this flag because each request may hit the DB from a
# different thread; other databases (e.g. Postgres) don't need it.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables on startup if they don't exist yet."""
    from ..models import models  # noqa: F401 - import so tables register with Base
    Base.metadata.create_all(bind=engine)
