@echo off
setlocal
cd /d "%~dp0"

set "PG_CTL=C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe"
set "PGDATA=%cd%\pgdata17"
set "PGPORT=55432"

echo [DB] Starting PostgreSQL on port %PGPORT% ...
echo     PGDATA = %PGDATA%
echo.

REM -w waits until server is up
REM -o passes options to postgres
start "" /min "%PG_CTL%" -D "%PGDATA%" -o "-p %PGPORT%" -w start

echo [DB] Done.
endlocal
