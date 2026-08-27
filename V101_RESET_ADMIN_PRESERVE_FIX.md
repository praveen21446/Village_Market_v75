# Village Market v101 — Reset Admin Preservation Fix

The v100 reset safety check assumed every admin had an `admin_accounts` row.
Village Market's primary admin is configured through Railway `ADMIN_ID` /
`ADMIN_PASSWORD`, and the primary admin user can exist only as `users.role='superadmin'`.

v101 now preserves:
- every `users.role='superadmin'` row
- every user referenced by `admin_accounts`
- all `admin_accounts` rows
- Railway ADMIN_ID / ADMIN_PASSWORD configuration

It still deletes:
- buyers/farmers
- crops
- bookings/orders
- reviews
- addresses
- notifications
- support tickets/messages
- OTP codes
- sessions
- referenced R2 crop photos (best effort)

Always run the dry run first:
`python reset_live_marketplace.py`

Execute only after checking the preserved admin list:
`python reset_live_marketplace.py --execute --confirm "RESET LIVE MARKETPLACE"`
