# Village Market v78 — MSG91 CAPTCHA Fix

- Removed the frontend-only CAPTCHA verification gate from the custom MSG91 OTP flow.
- MSG91 Widget Settings remain the source of truth for whether CAPTCHA is enabled or disabled.
- Preserved the v77 required MSG91 `success` / `failure` callbacks and SDK readiness polling.
- Preserved real SMS OTP, resend, server-side access-token verification, and Buyer/Farmer dual-role login.
