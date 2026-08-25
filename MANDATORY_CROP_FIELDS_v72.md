# Village Market v72

List a Crop validation update:
- Category, crop name, quantity, expected price, quality/grade, harvest date, details, and crop photo are mandatory.
- Required fields show a red `*`.
- Quantity must be at least 10 kg.
- Expected price must be greater than zero.
- Frontend prevents continuing when mandatory crop details are missing.
- Backend independently requires and validates mandatory crop fields, including details and crop photo.
- Frontend cache version bumped to v72.
