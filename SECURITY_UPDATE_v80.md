# Village Market v80 Security Update

This package adds production security/support files and baseline hardening while preserving the existing MSG91 OTP and Buyer/Farmer/Admin flows.

Changes include:
- Sanitized `.env.example` with no real/default production password.
- Expanded `.gitignore` and new `.dockerignore` to keep secrets, local DBs, uploads, backups and virtual environments out of source/build context.
- `SECURITY.md`, `SECURITY_CHECKLIST.md`, and `DEPLOYMENT_SECURITY.md`.
- Privacy Policy and Terms pages linked from login.
- Baseline security headers (nosniff, frame denial, referrer policy, permissions policy, HSTS in production).
- Production admin credentials must be configured explicitly.
- Crop upload validation: JPG/PNG/WEBP only, randomized stored filename, no application-side file-size ceiling; hosting/storage provider limits may still apply.
- Added idempotent `20260826_0004_fix_sessions_role.py` migration for production databases missing `sessions.role`.
- Removed local `.git`, local database contents, caches and sample/user upload files from the distributable ZIP.
- Frontend cache version bumped to v80.

Regression result: 9 tests passed.

Before public launch, customize Privacy Policy and Terms with actual business/legal contact, refund, delivery, dispute, retention and account-deletion policies.
