@echo off
title Village Market - Admin Server (Port 8001)
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
echo.
echo ========================================
echo Village Market Admin Server
echo URL: http://127.0.0.1:8001/admin
echo ========================================
echo.
start "Village Market Admin" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8001/admin"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
pause
