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
        # Drop any single-column unique constraint on fingerprint — name unknown, find it dynamically
        conn.execute(text("""
            DO $$
            DECLARE r RECORD;
            BEGIN
                FOR r IN
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_attribute att ON att.attrelid = rel.oid
                        AND att.attnum = ANY(con.conkey)
                    WHERE rel.relname = 'incidents'
                      AND con.contype = 'u'
                      AND att.attname = 'fingerprint'
                      AND array_length(con.conkey, 1) = 1
                LOOP
                    EXECUTE 'ALTER TABLE incidents DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname);
                END LOOP;
            END $$;
        """))
        # Also drop any unique index on fingerprint alone
        conn.execute(text("""
            DO $$
            DECLARE r RECORD;
            BEGIN
                FOR r IN
                    SELECT i.relname AS iname
                    FROM pg_index ix
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_class t ON t.oid = ix.indrelid
                    WHERE t.relname = 'incidents'
                      AND ix.indisunique = true
                      AND array_length(ix.indkey, 1) = 1
                      AND ix.indkey[0] = (
                          SELECT attnum FROM pg_attribute
                          WHERE attrelid = t.oid AND attname = 'fingerprint'
                      )
                LOOP
                    EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(r.iname);
                END LOOP;
            END $$;
        """))
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
