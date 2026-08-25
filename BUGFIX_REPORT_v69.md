# Village Market v69 Buyer Cart & Orders Fix

## Fixed
1. Cart badge now counts distinct cart items, not kilograms.
   - One crop at 10 kg => badge 1
   - One crop at 50 kg => badge 1
   - Two different crops => badge 2

2. Buyer Orders now separates Active Orders and Delivered Orders.
   - Active Orders excludes status `delivered`.
   - Delivered Orders contains only status `delivered`.
   - Delivered orders still support tracking/history and review.

3. Frontend cache version bumped to v69.

## Verification
- 6 pytest regression groups passed.
- frontend/app.js JavaScript syntax check passed.
- backend Python compile check passed.
- PostgreSQL/Alembic production configuration unchanged from v68.
