@echo off
setlocal
cd /d "%~dp0"

set "PG_CTL=C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe"
set "PGDATA=%cd%\pgdata17"
set "PGPORT=55432"
set "API_URL=http://127.0.0.1:8000/login"

echo ==========================================
echo  HR System - One Click Run
echo  DB : 127.0.0.1:%PGPORT%
echo  API: http://127.0.0.1:8000
echo ==========================================
echo.

REM 1) Start DB (minimized) and wait until ready
echo [1/4] Starting PostgreSQL...
start "" /min "%PG_CTL%" -D "%PGDATA%" -o "-p %PGPORT%" -w start

REM 2) Start API in a separate window (so this script can continue)
echo [2/4] Starting API server...
start "" /min cmd /c ""%cd%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

REM 3) Wait until API responds
echo [3/4] Waiting for API to be ready...
:waitloop
powershell -Command "try { (Invoke-WebRequest -UseBasicParsing %API_URL% -TimeoutSec 1).StatusCode | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  timeout /t 1 >nul
  goto waitloop
)

REM 4) Open browser after API is ready
echo [4/4] Opening browser...
start "" "%API_URL%"

echo Done.
endlocal
