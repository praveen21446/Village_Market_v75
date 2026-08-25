# Village Market v75 — Mobile polish, admin crop editing, dual role phone

- Fixed Buyer/Farmer mobile header alignment and kept language, notifications and Sign Out visible without overlap.
- Fixed Shopping Cart quantity controls so +/-/quantity/kg remain inside the card on narrow phones.
- Reduced mobile title overflow and improved small-screen card/button alignment.
- Admin can edit any published crop's name, category, quantity, expected price, current market price, quality, harvest date, details and admin note at any time.
- Market-price changes affect new purchases only; existing bookings retain their recorded order price.
- Same mobile number can now have separate Buyer and Farmer accounts and sign in to either role using the same OTP flow.
- Added Alembic migration 20260825_0003 for the `(phone, role)` uniqueness rule.
