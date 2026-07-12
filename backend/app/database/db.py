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
    upgrade_db_schema()


def upgrade_db_schema():
    """Run lightweight schema migrations to add missing columns to existing tables."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    with engine.begin() as conn:
        # Check users table columns
        if "users" in inspector.get_table_names():
            users_cols = [col["name"] for col in inspector.get_columns("users")]
            if "is_admin" not in users_cols:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
                    print("Migration: added column is_admin to users")
                except Exception as e:
                    print(f"Migration: could not add is_admin to users: {e}")

        # Check conversations table columns
        if "conversations" in inspector.get_table_names():
            conv_cols = [col["name"] for col in inspector.get_columns("conversations")]
            if "user_id" not in conv_cols:
                try:
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
                    print("Migration: added column user_id to conversations")
                except Exception as e:
                    print(f"Migration: could not add user_id to conversations: {e}")

        # Check uploaded_files table columns
        if "uploaded_files" in inspector.get_table_names():
            files_cols = [col["name"] for col in inspector.get_columns("uploaded_files")]
            if "conversation_id" not in files_cols:
                try:
                    conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE"))
                    print("Migration: added column conversation_id to uploaded_files")
                except Exception as e:
                    print(f"Migration: could not add conversation_id: {e}")
            if "message_id" not in files_cols:
                try:
                    conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE"))
                    print("Migration: added column message_id to uploaded_files")
                except Exception as e:
                    print(f"Migration: could not add message_id: {e}")
            if "user_id" not in files_cols:
                try:
                    conn.execute(text("ALTER TABLE uploaded_files ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
                    print("Migration: added column user_id to uploaded_files")
                except Exception as e:
                    print(f"Migration: could not add user_id to uploaded_files: {e}")


