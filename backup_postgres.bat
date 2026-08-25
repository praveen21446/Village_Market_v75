@echo off
cd /d "%~dp0"
if not exist .env (
echo.
echo ERROR: .env is missing.
echo Copy .env.example to .env and configure your PostgreSQL DATABASE_URL first.
echo See POSTGRESQL_SETUP.md.
pause
exit /b 1
)
if not exist .venv py -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts\backup_postgres.py
if errorlevel 1 (echo Backup failed.&pause&exit /b 1)
echo PostgreSQL backup completed.
pause
