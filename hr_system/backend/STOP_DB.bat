@echo off
setlocal
cd /d "%~dp0"

set "PG_CTL=C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe"
set "PGDATA=%cd%\pgdata17"

echo [DB] Stopping PostgreSQL...
"%PG_CTL%" -D "%PGDATA%" -m fast stop

echo [DB] Stopped.
endlocal
