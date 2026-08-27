# Railway Security Setup

Keep the Railway Start Command as:

```bash
alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Required production variables include `APP_ENV`, `DATABASE_URL`, `SECRET_KEY`, `ADMIN_ID`, `ADMIN_PASSWORD`, `MSG91_AUTH_KEY`, `MSG91_WIDGET_ID`, and `MSG91_WIDGET_TOKEN`.

Never copy the Railway `DATABASE_URL` or backend Auth Key into frontend JavaScript. The Widget ID/token are client widget configuration; the MSG91 Auth Key remains backend-only.

For uploads, `STORAGE_BACKEND=local` is suitable only for temporary testing. Use persistent object storage before relying on crop images in production.
