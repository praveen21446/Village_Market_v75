"""Copy existing Village Market SQLite data into a migrated PostgreSQL database.

Usage:
  set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/village_market
  python scripts/migrate_sqlite_to_postgres.py

The PostgreSQL schema must already be upgraded with: alembic upgrade head
"""
from __future__ import annotations
import argparse, os
from pathlib import Path
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = ROOT / "database" / "village_market.db"
TABLE_ORDER = [
    "users", "admin_accounts", "otp_codes", "sessions", "crops", "bookings",
    "reviews", "notifications", "saved_addresses",
]


def normalize_pg(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", default=str(DEFAULT_SQLITE), help="Source SQLite .db file")
    ap.add_argument("--postgres", default=os.getenv("DATABASE_URL", ""), help="Target PostgreSQL SQLAlchemy URL")
    ap.add_argument("--clear-target", action="store_true", help="Delete target rows first (development only)")
    args = ap.parse_args()
    sqlite_path = Path(args.sqlite).resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite source not found: {sqlite_path}")
    pg_url = normalize_pg(args.postgres.strip())
    if not pg_url or make_url(pg_url).get_backend_name() != "postgresql":
        raise SystemExit("Set --postgres or DATABASE_URL to a PostgreSQL URL.")

    src = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    dst = create_engine(pg_url, pool_pre_ping=True)
    src_tables = set(inspect(src).get_table_names())
    dst_tables = set(inspect(dst).get_table_names())
    missing = [t for t in TABLE_ORDER if t in src_tables and t not in dst_tables]
    if missing:
        raise SystemExit(f"Target schema is missing tables {missing}. Run: alembic upgrade head")

    src_meta, dst_meta = MetaData(), MetaData()
    src_meta.reflect(bind=src)
    dst_meta.reflect(bind=dst)

    with dst.begin() as dc:
        if args.clear_target:
            for name in reversed(TABLE_ORDER):
                if name in dst_tables:
                    dc.execute(dst_meta.tables[name].delete())
        else:
            populated = []
            for name in TABLE_ORDER:
                if name in dst_tables and dc.execute(select(dst_meta.tables[name]).limit(1)).first():
                    populated.append(name)
            if populated:
                raise SystemExit("Target contains data. Use an empty PostgreSQL DB or --clear-target explicitly.")

        copied = 0
        with src.connect() as sc:
            for name in TABLE_ORDER:
                if name not in src_tables or name not in dst_tables:
                    continue
                rows = [dict(r._mapping) for r in sc.execute(select(src_meta.tables[name])).all()]
                if rows:
                    target_cols = set(dst_meta.tables[name].c.keys())
                    clean = [{k: v for k, v in row.items() if k in target_cols} for row in rows]
                    dc.execute(dst_meta.tables[name].insert(), clean)
                    copied += len(clean)
                    print(f"{name}: {len(clean)} row(s)")

        # PostgreSQL integer sequences do not automatically advance after explicit ID inserts.
        for name in TABLE_ORDER:
            if name in dst_tables and "id" in dst_meta.tables[name].c:
                dc.execute(text(
                    "SELECT setval(pg_get_serial_sequence(:tbl, 'id'), "
                    "COALESCE((SELECT MAX(id) FROM " + name + "), 1), "
                    "COALESCE((SELECT MAX(id) FROM " + name + "), 0) > 0)"
                ), {"tbl": name})
    print(f"Migration complete. Copied {copied} total row(s).")

if __name__ == "__main__":
    main()
