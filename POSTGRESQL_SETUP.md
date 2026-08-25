# Village Market v68 — PostgreSQL Production Database

## What changed

- PostgreSQL is the production database target through `DATABASE_URL`.
- Alembic owns all production schema creation/changes.
- `backend.main` no longer runs `Base.metadata.create_all()` or ad-hoc `ALTER TABLE` statements.
- PostgreSQL connection pooling is configured through environment variables.
- Existing SQLite data can be copied once into PostgreSQL.
- Timestamped PostgreSQL backups and restore scripts are included.

## 1. Install PostgreSQL

Use PostgreSQL 16+ locally/server-side, or use a managed PostgreSQL provider. Create a database and user such as:

- Database: `village_market`
- User: `village_market`
- Password: choose a strong private password

For local development with Docker, `docker compose up -d postgres` can start PostgreSQL. Set `POSTGRES_PASSWORD` before using it outside disposable local development.

## 2. Configure `.env`

Copy `.env.example` to `.env` and replace the sample password:

`DATABASE_URL=postgresql+psycopg://village_market:YOUR_PASSWORD@127.0.0.1:5432/village_market`

Also replace `SECRET_KEY` and the production Admin password.

## 3. Create/upgrade schema

Run:

`python -m alembic upgrade head`

On Windows you can run `migrate_database.bat`. The normal Windows launchers also apply pending migrations before starting the server.

## 4. Move existing SQLite data (one time)

First create the PostgreSQL schema with Alembic. Then run:

`python scripts/migrate_sqlite_to_postgres.py`

Default SQLite source is `database/village_market.db`. The target is read from `DATABASE_URL`.

The target must be empty unless `--clear-target` is explicitly supplied. The migration preserves IDs and advances PostgreSQL sequences afterward.

## 5. Backups

Run `backup_postgres.bat` or:

`python scripts/backup_postgres.py`

Backups are written to `backups/village_market_YYYYMMDD_HHMMSS.dump`. PostgreSQL client tools (`pg_dump`) must be installed and available on PATH.

## 6. Restore

Run:

`restore_postgres.bat backups\\village_market_YYYYMMDD_HHMMSS.dump`

or:

`python scripts/restore_postgres.py backups/village_market_YYYYMMDD_HHMMSS.dump --clean`

Restore to a test database periodically to verify backups are usable.

## Migration workflow for future model changes

1. Change SQLAlchemy models.
2. Create a migration: `python -m alembic revision --autogenerate -m "describe change"`
3. Review the generated migration carefully.
4. Test it on a copy/staging database.
5. Apply with `python -m alembic upgrade head` before starting the new app version.

Never delete the production database to apply a model change.
