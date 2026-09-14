@echo off
echo ======================================================================
echo   Starting CampusOps AI - Autonomous Institutional Phone Operations
echo ======================================================================
echo.

REM Seed local SQLite database if not already present
echo [1/3] Ensuring institutional database is seeded...
call .\.venv\Scripts\python.exe scripts\seed_students.py --target sqlite

echo.
echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "CampusOps AI Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload"

echo.
echo [3/3] Starting React Command Center on http://localhost:5173 ...
cd web
start "CampusOps AI Web UI" cmd /k "npm run dev"

echo.
echo ======================================================================
echo   CampusOps AI is running!
echo   Dashboard:  http://localhost:5173
echo   Swagger:    http://127.0.0.1:8000/docs
echo ======================================================================
echo.
pause
