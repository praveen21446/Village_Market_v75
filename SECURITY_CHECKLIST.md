# Production Security Checklist

- [ ] Railway `APP_ENV=production`
- [ ] Strong `ADMIN_ID` and unique `ADMIN_PASSWORD` stored only in Railway
- [ ] `MSG91_AUTH_KEY` stored only in Railway and rotated if exposed
- [ ] Strong random `SECRET_KEY` stored only in Railway
- [ ] Railway Postgres `DATABASE_URL` configured by service reference
- [ ] PostgreSQL public networking disabled unless specifically required
- [ ] Database backups enabled and a restore test completed
- [ ] Production images moved to S3/R2/Supabase or another persistent object store
- [ ] `STORAGE_BACKEND` set to the chosen production storage
- [ ] OTP resend/throttling configured in MSG91
- [ ] Admin login tested with wrong-password rejection
- [ ] Buyer/Farmer role authorization tested
- [ ] File upload type and size validation tested
- [ ] Privacy Policy updated with owner/business contact details
- [ ] Terms updated with actual marketplace/payment/delivery policies
- [ ] No `.env`, database file, backup, user upload, or secret committed to GitHub
- [ ] Previously exposed keys/tokens rotated
- [ ] HTTPS domain tested on Android and desktop
