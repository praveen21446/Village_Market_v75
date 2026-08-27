# Village Market v89 - Cloudflare R2 crop photo storage

This build stores new crop photos in Cloudflare R2 instead of Railway local disk when `STORAGE_BACKEND=r2` (or `s3`).

## Railway variables

Set these on the Village Market application service only:

- `STORAGE_BACKEND=r2`
- `S3_BUCKET=village-market-images`
- `S3_REGION=auto`
- `S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
- `S3_ACCESS_KEY_ID=<R2 Access Key ID>`
- `S3_SECRET_ACCESS_KEY=<R2 Secret Access Key>`
- `S3_PUBLIC_BASE_URL=https://pub-<PUBLIC_ID>.r2.dev`

Do not commit real access keys to GitHub.

`S3_ENDPOINT_URL` must be the account-level endpoint. If a bucket-specific URL is pasted, the backend strips `/village-market-images` automatically.

New objects are stored under `crop-images/<farmer_id>/...` and returned as permanent public R2 URLs. Existing crops that point to deleted Railway `/uploads/...` files are not automatically recovered; re-upload those crop photos or create new listings.
