# v81 Multiple Crop Photos

- Farmers must upload at least 1 crop photo.
- Farmers can select multiple photos in one upload.
- Maximum defaults to 8 photos per crop (`MAX_CROP_PHOTOS`).
- JPG, PNG and WEBP validation and per-file size limits remain enforced.
- Existing single-photo crops remain compatible; their current `photo` becomes the primary photo.
- API responses now include both `photo` (primary) and `photos` (all images).
- Alembic migration `20260827_0005_crop_multiple_photos.py` adds `crops.photos_json`.
