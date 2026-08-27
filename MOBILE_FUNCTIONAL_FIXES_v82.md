# Village Market v82 — Mobile functional fixes + fresh start

Changes in this release:

- Cart quantity controls redesigned on phones so minus, quantity, and plus stay visible without horizontal overflow.
- Buyer Cancel Order confirmation now uses direct JavaScript event handlers, disables during submission, reports errors, and refreshes Active Orders after success.
- Live Support Open/Closed counters are now real filter buttons; tapping Closed shows closed tickets. Close/Reopen actions use explicit handlers and refresh immediately.
- Farmer Accept/Reject buttons now use explicit event handlers and busy protection; reject modal uses explicit handlers and error feedback.
- Farmer booking text cleaned up (`20 kg order`, not `20 kg kg order`) and harvest date spacing fixed.
- One-time Alembic migration `20260827_0006_fresh_start_reset.py` clears existing buyer/farmer/crop/order/support/address/notification/session data while preserving admin accounts and their superadmin users.
- Frontend cache version bumped to v82.

## Important
The `0006` migration intentionally deletes existing marketplace data on the first Railway deployment that reaches this revision. It cannot restore deleted data. Back up PostgreSQL before deploying if you may need the old data later.
