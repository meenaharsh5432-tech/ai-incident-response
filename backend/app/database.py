from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import user, incident, error, feedback, api_key  # noqa: register models

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    # Idempotent schema migrations — safe to run on every startup
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"))
        conn.execute(text("ALTER TABLE errors ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"))
        conn.execute(text("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"))
        # Drop any single-column unique constraint on fingerprint (try common names)
        conn.execute(text("ALTER TABLE incidents DROP CONSTRAINT IF EXISTS incidents_fingerprint_key"))
        conn.execute(text("ALTER TABLE incidents DROP CONSTRAINT IF EXISTS uq_incidents_fingerprint"))
        conn.execute(text("DROP INDEX IF EXISTS incidents_fingerprint_key"))
        # Replace with per-user composite unique index
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_incident_fingerprint_user "
            "ON incidents(fingerprint, user_id)"
        ))
        conn.commit()

    # Create IVFFlat index for fast approximate similarity search
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS incidents_embedding_idx
            ON incidents
            USING ivfflat (representative_embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS errors_embedding_idx
            ON errors
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
        conn.commit()
