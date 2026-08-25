# Village Market v64 - Fix & Regression Test Report

This package is based on the supplied v63 project and keeps the existing SQLite database file intact.

## Automated local checks passed

- Buyer OTP login and Farmer OTP login
- Admin login and invalid-admin rejection
- Role-based access restrictions
- Buyer/farmer session restore API (`/api/me`)
- Delivery/farm saved-address create, deduplicate, list, ownership and delete
- Farmer crop submission
- Admin pending-crop inspection list
- Admin crop approve/reject/remove flows
- Marketplace category/list/detail endpoints and private farmer-data hiding
- Low-stock marketplace hiding and farmer Add Stock restoration
- Buyer order creation and immediate visibility in Buyer and Farmer Bookings
- Cart checkout with multiple crops
- Farmer accept/reject flow
- Buyer cancellation and stock restoration
- Admin cancellation and stock restoration
- Admin confirmation -> tracking -> shipped transitions
- Buyer delivery OTP generation and visibility
- Incorrect OTP rejection
- Correct buyer OTP -> Delivered
- Delivered order review and duplicate-review prevention
- Buyer/farmer notifications, mark read and dismiss
- Farmer dashboard, farmer crop list, admin farmer list and admin analytics
- Static Buyer/Farmer and Admin pages
- Frontend JavaScript syntax checks
- HTTPS WebSocket protocol selection
- Live WebSocket broadcast test after crop submission
- SQLite `PRAGMA integrity_check`: OK
- `.env` automatic loading check

Run the included regression suite on Windows with `run_tests.bat`.

## Important external-service note

The local application behavior is tested. Live Razorpay, Twilio, SMTP, S3/R2 and browser geolocation/reverse-geocoding depend on real external credentials, internet access and browser permissions, so those third-party services cannot be fully live-tested without your accounts/keys. The project keeps their configuration hooks intact.
