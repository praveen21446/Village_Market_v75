import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Production uses PostgreSQL through DATABASE_URL. Tests/local compatibility may
# explicitly provide SQLite, but there is no implicit production SQLite database.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required. Copy .env.example to .env and configure PostgreSQL. "
        "For isolated local compatibility only, use .env.local-sqlite.example explicitly."
    )

# Some hosting providers still expose postgres:// URLs. SQLAlchemy expects
# postgresql://, and psycopg v3 is selected explicitly.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]

url = make_url(DATABASE_URL)
is_sqlite = url.get_backend_name() == "sqlite"
engine_kwargs = {"pool_pre_ping": True}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
