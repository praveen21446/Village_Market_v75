"""Create timestamped PostgreSQL custom-format backups using pg_dump."""
from pathlib import Path
from datetime import datetime
import os, shutil, subprocess, sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
url = os.getenv("DATABASE_URL", "")
if "postgres" not in url:
    raise SystemExit("DATABASE_URL must point to PostgreSQL.")
cli_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
pg_dump = shutil.which("pg_dump")
if not pg_dump:
    raise SystemExit("pg_dump was not found. Install PostgreSQL client tools and add them to PATH.")
out_dir = ROOT / "backups"
out_dir.mkdir(exist_ok=True)
out = out_dir / f"village_market_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"
subprocess.run([pg_dump, "--format=custom", "--no-owner", "--no-acl", "--file", str(out), cli_url], check=True)
print(out)
