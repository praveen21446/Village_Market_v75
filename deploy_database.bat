@echo off

echo ============================
echo Village Market Deployment
echo ============================

echo.
echo Step 1 - Backup Database
python scripts\backup_postgres.py

if errorlevel 1 (
    echo Backup failed.
    pause
    exit /b 1
)

echo.
echo Step 2 - Run Alembic
python -m alembic upgrade head

if errorlevel 1 (
    echo Migration failed.
    pause
    exit /b 1
)

echo.
echo Deployment Complete
pause