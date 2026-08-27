# Village Market v100 — Safe Fresh Start Reset

This release adds `reset_live_marketplace.py`.

It preserves existing Admin accounts/password hashes and the PostgreSQL/Alembic schema.
It clears non-admin users and marketplace data, and best-effort deletes crop images referenced in R2.

## Safety workflow
Run a dry run first in the environment that contains the LIVE Railway `DATABASE_URL` and R2 variables:

`python reset_live_marketplace.py`

Nothing is deleted during the dry run.

Only after checking the database and preserved admin list, execute:

`python reset_live_marketplace.py --execute --confirm "RESET LIVE MARKETPLACE"`

The script refuses to execute without the exact confirmation phrase.
It also refuses SQLite by default.

Important: running this from a normal local CMD with a local DATABASE_URL resets the local database, not Railway.
For the live database, run it in an environment configured with the live Railway DATABASE_URL and R2 credentials.
