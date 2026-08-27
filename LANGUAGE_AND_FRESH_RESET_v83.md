# Village Market v83

- Telugu/Hindi translation coverage added for Live Support, Buyer Orders, Farmer Orders, Dashboard labels, statuses, buttons and empty states.
- Language switching rerenders the active page immediately.
- A new one-time migration `20260827_0007_force_fresh_start.py` clears all crops, orders, buyers, farmers, reviews, addresses, notifications, OTP records and support conversations while preserving admin accounts.
- Browser cart/session draft data is cleared once after v83 deployment so old local cart content does not reappear.
