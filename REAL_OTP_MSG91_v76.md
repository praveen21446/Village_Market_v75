# Village Market v76 — MSG91 Real OTP

## What changed
- Replaced the production demo OTP login flow with MSG91 OTP Widget (custom Web SDK UI).
- Added 4-digit OTP entry, resend flow, CAPTCHA container, and request-id handling.
- Added secure server-side `verifyAccessToken` validation before a Village Market session is created.
- Preserved the same-phone Buyer/Farmer dual-role session behavior.
- Demo OTP endpoints are now disabled when `APP_ENV=production`; they remain only for isolated local regression tests.
- MSG91 Authkey stays server-side in Railway. Widget ID/token are obtained through a public config endpoint from environment variables.

## Railway variables required
```
MSG91_AUTH_KEY=<secret backend authkey>
MSG91_WIDGET_ID=<OTP widget id>
MSG91_WIDGET_TOKEN=<OTP widget client token>
APP_ENV=production
```

## MSG91 widget settings recommended for the first live test
- Default channel: SMS
- Verification type: OTP
- OTP length: 4 digits
- CAPTCHA: Enabled (the login page now provides a CAPTCHA render container)
- Invisible OTP: Disable for the first SMS-only test
- User existence validation: Off
- Webhook: Skipped/off
- Country restriction: India (+91) recommended

## Security
Never commit `MSG91_AUTH_KEY` to GitHub or frontend code. If an Authkey is exposed, revoke it in MSG91 and update Railway.
