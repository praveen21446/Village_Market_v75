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
if errorlevel 1 (echo Installation failed.&pause&exit /b 1)
python -m alembic upgrade head
if errorlevel 1 (echo Database migration failed. Check DATABASE_URL in .env.&pause&exit /b 1)
echo Database is at the latest migration.
pause
