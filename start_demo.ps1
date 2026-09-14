# CampusOps AI - 1-Click Launch Script (PowerShell)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Starting CampusOps AI - Autonomous Institutional Phone Operations" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Seed database
Write-Host "[1/3] Ensuring institutional database is seeded..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" scripts\seed_students.py --target sqlite

# 2. Launch Backend
Write-Host "[2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --port 8000 --reload"

# 3. Launch Frontend
Write-Host "[3/3] Starting React Command Center on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\web'; npm run dev"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  CampusOps AI is running!" -ForegroundColor Green
Write-Host "  Dashboard:  http://localhost:5173" -ForegroundColor Green
Write-Host "  Swagger:    http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
