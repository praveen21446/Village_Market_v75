\
#!/usr/bin/env sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
mkdir -p backups
STAMP="$(date -u +%Y%m%d_%H%M%S)"
pg_dump "$DATABASE_URL" -Fc -f "backups/village_market_${STAMP}.dump"
echo "Backup created: backups/village_market_${STAMP}.dump"
