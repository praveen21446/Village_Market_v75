# Village Market v66 Test Report

Result: **5 automated regression test groups passed**.

Covered flows include:

- Buyer and Farmer OTP authentication and role access
- Same-phone Buyer/Farmer role corruption protection
- Admin login, additional admin creation/login/removal
- Saved addresses
- Farmer crop submission
- Admin crop approval/rejection/removal
- Buyer marketplace visibility and private farmer data protection
- Single order creation and immediate visibility in Buyer and Farmer Bookings
- Cart checkout with multiple crops
- Farmer Accept/Reject and stock restoration
- Buyer cancellation and stock restoration
- Admin cancellation and stock restoration
- Admin confirmation and tracking transitions
- Shipped status and buyer delivery OTP
- Admin OTP verification before Delivered
- Delivered review flow
- Low-stock marketplace hiding and Add Stock restoration
- Notifications and WebSocket endpoint
- Frontend no-cache headers and v66 cache-busting assets
- JavaScript syntax, backend import and SQLite integrity

Important v66 fix: a mobile number already registered as Buyer cannot silently become Farmer, and vice versa. This prevents orders/bookings from disappearing because the user's role changed during testing.
