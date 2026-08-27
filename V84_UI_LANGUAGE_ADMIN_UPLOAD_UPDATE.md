# Village Market v84 update

- Language switches in-place without reloading/re-requesting the current page.
- Expanded Telugu/Hindi UI translation coverage.
- Buyer cart requires an address first; after an address exists the primary action is Place Order.
- Mobile cart quantity control is compact.
- Admin Users screen added; admin can edit/verify/delete buyer/farmer accounts and related data.
- Admin can permanently delete orders in addition to controlling order statuses.
- Crop image application-side file-size restriction removed. Image-type validation and the maximum photo-count setting remain. Hosting/storage providers may impose their own technical upload limits.
- Added migration `20260827_0008_final_fresh_start.py` to guarantee one final clean start: all buyer/farmer/crop/order/support/address/session data is removed while admin accounts are preserved.
