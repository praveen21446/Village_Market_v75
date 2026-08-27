# Village Market Security Policy

## Reporting a security issue
Do not post passwords, API keys, database URLs, OTP tokens, user phone numbers, addresses, or security vulnerabilities in public GitHub issues.

For a production launch, configure a private security contact email and replace this line with that address before publishing the repository.

## Secrets
- Keep `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`, `MSG91_AUTH_KEY`, SMTP credentials, payment secrets, and cloud-storage secrets only in Railway Variables or another secret manager.
- Never commit a production `.env` file.
- Rotate any credential that appears in screenshots, chat messages, logs, Git history, or public repositories.

## Authentication
- Buyer/Farmer phone ownership is verified through MSG91 OTP.
- Admin credentials must be explicitly configured in production.
- Sessions expire and role checks are enforced server-side.

## Data protection
- Use HTTPS in production.
- Do not expose PostgreSQL publicly unless there is a specific administrative need.
- Back up PostgreSQL regularly and test restores.
- Move production crop images to persistent object storage rather than ephemeral application storage.

## File uploads
Only JPG, PNG and WEBP crop images are accepted. The default maximum upload size is 5 MB and can be configured with `MAX_UPLOAD_MB`.

## Dependency maintenance
Review and update Python dependencies regularly. Test upgrades before deploying them to production.
