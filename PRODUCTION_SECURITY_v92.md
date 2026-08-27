# Village Market v92 — Production Security

Implemented:
- Production startup refuses missing DB/admin/MSG91/R2 secrets.
- Production refuses SQLite.
- HTTPS redirect when Railway forwards HTTP.
- HSTS, CSP, frame, MIME, referrer and permissions security headers.
- Admin login throttling: 5 attempts / 5 minutes per instance/key.
- MSG91 login exchange throttling: 8 attempts / minute per instance/key.
- Secondary admin passwords use PBKDF2-HMAC-SHA256 with 600,000 iterations and random salt.
- Existing hashed secondary-admin passwords remain verifiable.
- RBAC remains enforced through `require_role`.
- Crop uploads remain limited to JPG/PNG/WEBP; no app-side byte limit per product requirement.
- `.gitignore` blocks `.env`, private keys, local DBs, backups and uploaded files.
- `security_check.py` checks for common accidentally committed secrets.
- `backup_postgres.sh` provides a PostgreSQL dump command.

Railway Variables required in production:
APP_ENV=production
DATABASE_URL=<Railway PostgreSQL URL>
ADMIN_ID=<private admin id>
ADMIN_PASSWORD=<strong 12+ character password>
MSG91_AUTH_KEY=<secret>
MSG91_WIDGET_ID=<id>
MSG91_WIDGET_TOKEN=<client token>
STORAGE_BACKEND=r2
S3_BUCKET=village-market-images
S3_REGION=auto
S3_ENDPOINT_URL=<Cloudflare account R2 endpoint>
S3_ACCESS_KEY_ID=<secret>
S3_SECRET_ACCESS_KEY=<secret>
S3_PUBLIC_BASE_URL=<public r2.dev/custom-domain URL>

Operational actions that code cannot perform automatically:
1. Verify the real secret values exist only in Railway Variables and rotate any key ever committed/shared.
2. Enable Railway/PostgreSQL backups or schedule `pg_dump` to durable off-platform storage.
3. Keep Cloudflare R2 API token scoped only to the required bucket.
4. Run `python security_check.py` before every release.
5. Review GitHub history too: `.gitignore` prevents future commits but does not erase old secrets from history.
