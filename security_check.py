from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parent
skip={'.git','.venv','venv','__pycache__','.pytest_cache'}
bad_files=[]; hits=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in skip for x in p.parts): continue
    rel=p.relative_to(ROOT)
    if p.name=='.env': bad_files.append(str(rel))
    if p.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.zip','.db','.sqlite','.dump','.backup'}: continue
    try:text=p.read_text(encoding='utf-8')
    except Exception:continue
    # High-confidence credential shapes only; examples/placeholders are ignored.
    for pat in [
        r'AKIA[0-9A-Z]{16}',
        r'(?i)S3_SECRET_ACCESS_KEY\s*=\s*[A-Za-z0-9/+]{30,}',
        r'(?i)MSG91_AUTH_KEY\s*=\s*[A-Za-z0-9]{20,}',
        r'(?i)RAZORPAY_KEY_SECRET\s*=\s*[A-Za-z0-9]{20,}',
        r'postgres(?:ql)?(?:\+psycopg)?://[^:\s/]+:[^@\s]+@[A-Za-z0-9.-]+(?::\d+)?/[A-Za-z0-9_-]+',
    ]:
        for m in re.finditer(pat,text):
            v=m.group(0)
            if any(x in v for x in ['USER:PASSWORD','user:pass','YOUR_','<secret>','<Railway']):continue
            if 'DATABASE_URL[len(' in v:continue
            hits.append(f'{rel}: potential credential')
print('Secret files:', bad_files or 'none')
print('Potential committed secrets:', hits or 'none')
if bad_files or hits:sys.exit(1)
print('SECURITY CHECK PASSED')
