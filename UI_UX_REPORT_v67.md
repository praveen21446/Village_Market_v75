# Village Market v67 — Buyer/Farmer UI/UX Finalization

## Completed
- Mobile-first app shell with compact header and fixed bottom navigation.
- Role-aware Buyer/Farmer navigation with active-page indication.
- Larger touch targets, focus states, safer mobile form sizing and responsive layouts.
- Marketplace cards redesigned for phone/tablet/desktop layouts.
- Cart changed to mobile cards instead of a compressed desktop table.
- Buyer order cards, delivery OTP and tracking timeline made mobile-friendly.
- Farmer bookings, crop details, dashboard statistics and actions improved for mobile.
- Loading feedback added for API activity using a non-blocking progress indicator.
- Error/empty states improved with clear recovery actions.
- Toast notifications improved for readability above mobile bottom navigation.
- Login UI cleaned up; demo-style static message removed. Local testing OTP is only shown when returned by the local backend.
- Cache version bumped to v67 so browsers load the new CSS/JavaScript.

## Scope intentionally unchanged
Backend business rules, database schema, OTP provider, payment provider and admin workflow are unchanged in this UI/UX release.
