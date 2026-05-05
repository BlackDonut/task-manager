@echo off
REM =====================================================================
REM start-dev.bat - 開発用のバックエンドとフロントエンドを同時に起動するスクリプト。
REM ---------------------------------------------------------------------
REM 起動するプロセス:
REM   1. Backend  : uvicorn (FastAPI, ポート 8000) → 別ウインドウで PowerShell 起動
REM   2. Frontend : vite dev   (ポート 5173) → 別ウインドウで PowerShell 起動
REM
REM 前提条件 (セットアップ済みであること):
REM   - Python 仮想環境 (.venv) 作成済み かつ pip install -e ".[dev]" 実行済み
REM   - frontend/node_modules 存在 (cd frontend && npm install 実行済み)
REM
REM 修正履歴メモ (初学者向け註釈):
REM   %~dp0 は末尾にバックスラッシュを含むため、"%~dp0.." は相対パス文字列
REM   （例: "scripts\.."）のままになる。PowerShell の -LiteralPath は相対パスを
REM   解決できずエラーとなるため、pushd / popd で一旦親ディレクトリへ移動して
REM   %CD% (絶対パス) を REPO_ROOT に保存している。
REM =====================================================================

setlocal

REM --- リポジトリルートの絶対パスを pushd/popd で解決し REPO_ROOT に記録 ---
pushd "%~dp0.."
set "REPO_ROOT=%CD%"
popd

echo [start-dev] Repository root: %REPO_ROOT%

REM --- 前提条件の確認 (セットアップ漏れを検出、警告のみで起動は続行) ---
if not exist "%REPO_ROOT%\.venv\Scripts\Activate.ps1" (
    echo [start-dev] WARNING: .venv not found. Run: python -m venv .venv ^&^& pip install -e ".[dev]"
)
if not exist "%REPO_ROOT%\frontend\node_modules" (
    echo [start-dev] WARNING: node_modules not found. Run: cd frontend ^&^& npm install
)

REM --- 環境変数のデフォルト値を設定 (未設定なら development) ---
if "%APP_ENV%"=="" set "APP_ENV=development"

REM --- バックエンド (uvicorn) を別ウインドウの PowerShell で起動 ---
echo [start-dev] Starting backend (uvicorn) on http://localhost:8000 ...
start "task-manager: backend" powershell -NoExit -ExecutionPolicy Bypass -Command ^
  "Set-Location -LiteralPath '%REPO_ROOT%';" ^
  "if (Test-Path '.venv\Scripts\Activate.ps1') { . .\.venv\Scripts\Activate.ps1 };" ^
  "$env:APP_ENV='%APP_ENV%';" ^
  "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM --- フロントエンド (vite) を別ウインドウの PowerShell で起動 ---
echo [start-dev] Starting frontend (vite) on http://localhost:5173 ...
start "task-manager: frontend" powershell -NoExit -ExecutionPolicy Bypass -Command ^
  "Set-Location -LiteralPath '%REPO_ROOT%\frontend';" ^
  "npm run dev"

echo.
echo [start-dev] Launched backend and frontend in separate windows.
echo [start-dev]   Backend  : http://localhost:8000  (docs: http://localhost:8000/docs)
echo [start-dev]   Frontend : http://localhost:5173
echo [start-dev] To stop, run scripts\stop-dev.bat

endlocal
