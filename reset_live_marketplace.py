"""
Village Market production fresh-start reset.

PRESERVES:
- users referenced by admin_accounts
- admin_accounts and admin password hashes
- database schema / alembic_version
- environment/Railway/R2/MSG91 configuration

DELETES:
- all non-admin users
- crops, bookings, reviews, addresses
- notifications, support tickets/messages
- OTP codes
- all sessions (admins simply sign in again)
- crop image objects referenced by crop records (best effort)

Safety:
- requires --execute
- requires exact confirmation text
- refuses SQLite unless --allow-local is supplied
"""
import argparse, json, os, sys
from urllib.parse import urlparse, unquote

from sqlalchemy import create_engine, inspect, text

CONFIRM = "RESET LIVE MARKETPLACE"

def mask_db(url):
    try:
        u=urlparse(url.replace("postgresql+psycopg://","postgresql://",1))
        return f"{u.scheme}://{u.hostname or '?'}:{u.port or ''}/{(u.path or '/').lstrip('/')}"
    except Exception:
        return "<configured database>"

def r2_client():
    backend=os.getenv("STORAGE_BACKEND","local").lower()
    bucket=os.getenv("S3_BUCKET","").strip()
    if backend not in {"s3","r2"} or not bucket:
        return None, None
    import boto3
    endpoint=(os.getenv("S3_ENDPOINT_URL") or "").strip().rstrip("/")
    if endpoint.endswith("/"+bucket):
        endpoint=endpoint[:-(len(bucket)+1)]
    access=(os.getenv("S3_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID") or "").strip()
    secret=(os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY") or "").strip()
    region=(os.getenv("S3_REGION") or os.getenv("AWS_REGION") or "auto").strip()
    kw={"region_name":region}
    if endpoint: kw["endpoint_url"]=endpoint
    if access: kw["aws_access_key_id"]=access
    if secret: kw["aws_secret_access_key"]=secret
    return boto3.client("s3",**kw), bucket

def photo_keys(conn):
    keys=set()
    base=(os.getenv("S3_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    for row in conn.execute(text("SELECT photo, photos_json FROM crops")).mappings():
        urls=[]
        if row["photo"]: urls.append(row["photo"])
        try:
            vals=json.loads(row["photos_json"] or "[]")
            if isinstance(vals,list): urls.extend(vals)
        except Exception:
            pass
        for value in urls:
            if not value: continue
            value=str(value).strip()
            if base and value.startswith(base+"/"):
                key=value[len(base)+1:]
            else:
                key=unquote(urlparse(value).path.lstrip("/"))
            if key: keys.add(key)
    return keys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--execute",action="store_true")
    ap.add_argument("--confirm",default="")
    ap.add_argument("--allow-local",action="store_true")
    args=ap.parse_args()

    db=os.getenv("DATABASE_URL","").strip()
    if not db:
        print("ERROR: DATABASE_URL is not set."); return 2
    if db.startswith("postgres://"):
        db="postgresql+psycopg://"+db[len("postgres://"):]
    elif db.startswith("postgresql://") and "+psycopg" not in db:
        db="postgresql+psycopg://"+db[len("postgresql://"):]

    is_sqlite=db.startswith("sqlite")
    if is_sqlite and not args.allow_local:
        print("REFUSED: this command is intended for PostgreSQL. Use --allow-local only for a deliberate local test.")
        return 2

    engine=create_engine(db,pool_pre_ping=True)
    with engine.connect() as conn:
        tables=set(inspect(conn).get_table_names())
        needed={"users","admin_accounts","crops","bookings"}
        missing=needed-tables
        if missing:
            print("ERROR: expected Village Market tables missing:",", ".join(sorted(missing))); return 2

        # Primary admin is configured through Railway ADMIN_ID/ADMIN_PASSWORD and may
        # exist only as a users.role='superadmin' row, without an admin_accounts row.
        # Secondary admins are stored in admin_accounts. Preserve BOTH forms.
        admins=conn.execute(text("""
            SELECT
                u.id,
                u.name,
                u.phone,
                u.role,
                a.admin_id,
                a.active
            FROM users u
            LEFT JOIN admin_accounts a ON a.user_id=u.id
            WHERE u.role='superadmin' OR a.user_id IS NOT NULL
            ORDER BY u.id
        """)).mappings().all()

        configured_primary_id=os.getenv("ADMIN_ID","").strip()
        configured_primary_password=os.getenv("ADMIN_PASSWORD","")
        if not admins and not (configured_primary_id and configured_primary_password):
            print("REFUSED: no preserved superadmin user/admin account was found and primary ADMIN_ID/ADMIN_PASSWORD are not configured.")
            return 2

        counts={}
        for table in ["users","admin_accounts","crops","bookings","reviews","saved_addresses",
                      "notifications","support_tickets","support_messages","otp_codes","sessions"]:
            if table in tables:
                counts[table]=conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()

        print("Database:",mask_db(db))
        print("Admins that WILL BE KEPT:")
        if admins:
            for a in admins:
                admin_label=a["admin_id"] or configured_primary_id or "(primary superadmin)"
                active=a["active"] if a["active"] is not None else True
                print(f"  user_id={a['id']} admin_id={admin_label} name={a['name']} role={a['role']} active={active}")
        else:
            print(f"  Primary Railway admin will be recreated on next login: admin_id={configured_primary_id}")
        print("Current row counts:")
        for k,v in counts.items(): print(f"  {k}: {v}")

        if not args.execute:
            print("\nDRY RUN ONLY. Nothing was deleted.")
            print(f'To execute, rerun with: --execute --confirm "{CONFIRM}"')
            return 0
        if args.confirm != CONFIRM:
            print("REFUSED: exact confirmation text was not supplied."); return 2

        keys=photo_keys(conn) if "crops" in tables else set()

    # Delete cloud objects BEFORE DB records so referenced keys are still known.
    deleted=failed=0
    if keys:
        try:
            s3,bucket=r2_client()
            if s3 and bucket:
                for key in keys:
                    try:
                        s3.delete_object(Bucket=bucket,Key=key); deleted+=1
                    except Exception as e:
                        failed+=1; print("R2 delete warning:",key,str(e))
            else:
                print("R2 deletion skipped: R2/S3 storage variables are not configured in this environment.")
        except Exception as e:
            print("R2 deletion warning:",e)
            failed=len(keys)

    admin_ids=[a["id"] for a in admins]

    # FK-safe deletion. Keep all superadmin user rows and all users referenced by admin_accounts.
    with engine.begin() as conn:
        def wipe(table):
            if table in tables: conn.execute(text(f'DELETE FROM "{table}"'))

        wipe("support_messages")
        wipe("support_tickets")
        wipe("reviews")
        wipe("notifications")
        wipe("saved_addresses")
        wipe("bookings")
        wipe("crops")
        wipe("otp_codes")
        wipe("sessions")  # sessions are temporary; admin credentials/accounts remain.

        # Keep primary superadmin users and secondary admin-account users.
        conn.execute(text("""
            DELETE FROM users
            WHERE role <> 'superadmin'
              AND id NOT IN (SELECT user_id FROM admin_accounts)
        """))

    with engine.connect() as conn:
        remaining_users=conn.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
        remaining_admins=conn.execute(text("SELECT COUNT(*) FROM admin_accounts")).scalar_one()
        remaining_crops=conn.execute(text("SELECT COUNT(*) FROM crops")).scalar_one()
        remaining_orders=conn.execute(text("SELECT COUNT(*) FROM bookings")).scalar_one()

    print("\nRESET COMPLETE")
    print("Secondary admin_accounts kept:",remaining_admins)
    print("Admin user rows remaining:",remaining_users)
    print("Crops:",remaining_crops)
    print("Bookings/orders:",remaining_orders)
    print(f"Referenced R2 crop images deleted: {deleted}; failed/skipped: {failed}")
    print("Admin sessions were cleared. Sign in again with the existing admin credentials.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
