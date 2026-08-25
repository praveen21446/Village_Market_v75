@echo off
title Village Market - Regression Tests
cd /d "%~dp0"
if not exist .venv py -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if errorlevel 1 (echo Installation failed.&pause&exit /b 1)
python -m pytest -q
if errorlevel 1 (
  echo.
  echo TESTS FAILED
  pause
  exit /b 1
)
echo.
echo ALL VILLAGE MARKET REGRESSION TESTS PASSED
pause
