@echo off
setlocal
cd /d "%~dp0"

echo [API] Starting Uvicorn on http://127.0.0.1:8000 ...
echo.

".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 


endlocal
