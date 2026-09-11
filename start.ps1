# DSA Tracker – start both servers
# Run this script from the project root directory.
# Backend runs on port 8001 (avoids collision with GreatKart on 8000).
# Frontend Vite dev server runs on port 5173 and proxies /api → 8001.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting DSA Tracker backend on 127.0.0.1:8001 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root\backend'; .\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001"
)

Write-Host "Starting DSA Tracker frontend on port 5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Both servers launched." -ForegroundColor Green
Write-Host "  Backend : http://127.0.0.1:8001/api/" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:5173/" -ForegroundColor Yellow
