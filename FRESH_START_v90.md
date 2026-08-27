# Village Market v90 — Fresh Start

This release adds migration `20260827_0009_restart_marketplace_clean.py`.

On the next Railway deployment, the normal start command:

    alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port $PORT

runs the reset exactly once.

## Removed from PostgreSQL
- Buyer/farmer users
- Crops
- Orders/bookings
- Reviews
- Saved addresses
- Notifications
- OTP records
- Sessions
- Live-support tickets and messages

## Preserved
- Admin accounts and the user rows backing those admin accounts
- Database schema
- Alembic history

## Cloudflare R2
Database migrations do not delete remote R2 objects. To remove old crop photos:
Cloudflare > R2 Object Storage > village-market-images > Objects, select the old
`crop-images` objects/folder and delete them.

Do not delete the bucket itself. New crop uploads will continue using the same bucket.
