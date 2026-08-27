# Village Market v91 — Automatic R2 crop photo deletion

When an admin removes a published crop from the buyer marketplace, Village Market
now performs a best-effort cleanup of every photo associated with that crop.

- Cloudflare R2 / S3: each object is deleted with `delete_object`.
- Local development: `/uploads/...` files are removed from disk.
- Crop `photo` and `photos_json` fields are cleared after cleanup.
- If an object was already missing, the crop removal still succeeds.
- Admin accounts, OTP, order flows, translations, R2 uploads, and v90 fresh-start
  behavior are otherwise unchanged.

Important: removing a crop is destructive for its photos. Restoring the crop later
would require uploading new photos.
