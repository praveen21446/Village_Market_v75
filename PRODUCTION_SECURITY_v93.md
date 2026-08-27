# Village Market v93 — Final Security Header Fix

- CSP allows required MSG91 resources.
- CSP allows Razorpay checkout resources.
- HSTS is enabled in production.
- Existing HTTPS redirect, RBAC, rate limiting, upload validation,
  R2 storage, and secret scanning remain enabled.

Railway must have:
APP_ENV=production
