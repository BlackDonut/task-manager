@echo off
REM =====================================================================
REM start-dev.bat
REM   1. Backend  : uvicorn on port 8000 (new PowerShell window)
REM   2. Frontend : vite dev on port 5173 (new PowerShell window)
REM
REM Requirements:
REM   - .venv created and pip install -e ".[dev]" done
REM   - frontend/node_modules present (npm install done)
REM
REM Note: pushd/popd is used to resolve the absolute path of the repo root
REM   because %~dp0 includes a trailing backslash and PowerShell -LiteralPath
REM   cannot resolve relative paths.
REM =====================================================================

setlocal

pushd "%~dp0.."
set "REPO_ROOT=%CD%"
popd

echo [start-dev] Repository root: %REPO_ROOT%

if not exist "%REPO_ROOT%\.venv\Scripts\Activate.ps1" (
    echo [start-dev] WARNING: .venv not found. Run: python -m venv .venv
)
if not exist "%REPO_ROOT%\frontend\node_modules" (
    echo [start-dev] WARNING: node_modules not found. Run: cd frontend ^&^& npm install
)

if "%APP_ENV%"=="" set "APP_ENV=development"

echo [start-dev] Starting backend  on http://localhost:8000 ...
start "task-manager: backend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%REPO_ROOT%'; if (Test-Path '.venv\Scripts\Activate.ps1') { . .venv\Scripts\Activate.ps1 }; $env:APP_ENV='%APP_ENV%'; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [start-dev] Starting frontend on http://localhost:5173 ...
start "task-manager: frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%REPO_ROOT%\frontend'; npm run dev"

echo.
echo [start-dev] Done. Backend: http://localhost:8000  Frontend: http://localhost:5173
echo [start-dev] To stop: scripts\stop-dev.bat

endlocal
