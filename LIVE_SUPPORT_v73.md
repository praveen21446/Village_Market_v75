# Village Market v73 — Live Support

Added a persistent Live Support module for Buyer, Farmer, and Admin.

- Buyer/Farmer navigation includes **Live Support**.
- Users can create categorized support tickets, send follow-up messages, close and reopen tickets.
- Admin portal includes **Live Support** to view all requests, see user name/role/phone, reply, close, and reopen.
- New messages create in-app notifications.
- WebSocket support-update events and 8-second polling keep open support views fresh.
- PostgreSQL schema is managed by Alembic revision `20260824_0002`.
