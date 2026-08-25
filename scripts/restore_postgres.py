"""Restore a Village Market pg_dump custom-format backup."""
from pathlib import Path
import argparse, os, shutil, subprocess
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
ap = argparse.ArgumentParser()
ap.add_argument("backup", help="Path to .dump backup")
ap.add_argument("--clean", action="store_true", help="Drop existing objects before restoring")
args = ap.parse_args()
url = os.getenv("DATABASE_URL", "")
if "postgres" not in url:
    raise SystemExit("DATABASE_URL must point to PostgreSQL.")
cli_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
pg_restore = shutil.which("pg_restore")
if not pg_restore:
    raise SystemExit("pg_restore was not found. Install PostgreSQL client tools and add them to PATH.")
backup = Path(args.backup).resolve()
if not backup.exists():
    raise SystemExit(f"Backup not found: {backup}")
cmd = [pg_restore, "--no-owner", "--no-acl", "--dbname", cli_url]
if args.clean:
    cmd += ["--clean", "--if-exists"]
cmd.append(str(backup))
subprocess.run(cmd, check=True)
print("Restore completed.")
