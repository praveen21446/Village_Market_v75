# Village Market v75

- Same verified mobile number can sign in as Buyer or Farmer; role is stored per login session.
- Admin can edit any published crop at any time, including market price, name, category, quality, available quantity, harvest date and details.
- Existing orders keep their booked price; admin market-price changes apply to new orders.
- Added additional mobile overflow, form, card, and published-crop action fixes for narrow phones.
- Added Alembic migration `20260825_0003_session_roles.py`.
