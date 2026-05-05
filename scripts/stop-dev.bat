@echo off
REM =====================================================================
REM stop-dev.bat - 開発用のバックエンド・フロントエンドプロセスを停止するスクリプト。
REM ---------------------------------------------------------------------
REM 該当ポートで LISTENING 状態のプロセスを netstat で探して taskkill する:
REM   - 8000 (uvicorn / FastAPI)
REM   - 5173 (vite / frontend)
REM
REM cmd.exe の正規表現・パイプ処理トラブルを避けるため PowerShell をインラインで呼ぶ。
REM 補足: PowerShell の $pid は予約変数なので $procId を使用している。
REM =====================================================================

echo [stop-dev] Stopping development servers...
REM --- 各ポートを LISTENING している PID を調べて強制終了させる ---
powershell -ExecutionPolicy Bypass -NoProfile -Command ^
  "$ports = @{8000='backend (uvicorn)'; 5173='frontend (vite)'};" ^
  "$ports.GetEnumerator() | ForEach-Object {" ^
  "  $port = $_.Key; $label = $_.Value;" ^
  "  $lines = netstat -ano | Select-String ('TCP\s+\S+:' + $port + '\s+\S+\s+LISTENING');" ^
  "  if ($lines) {" ^
  "    $lines | ForEach-Object {" ^
  "      $procId = ($_ -split '\s+')[-1];" ^
  "      if ($procId -match '^\d+$' -and $procId -ne '0') {" ^
  "        Write-Host \"[stop-dev] Killing $label on port $port (PID=$procId)\";" ^
  "        taskkill /F /PID $procId | Out-Null" ^
  "      }" ^
  "    }" ^
  "  } else {" ^
  "    Write-Host \"[stop-dev] No process listening on port $port ($label)\"" ^
  "  }" ^
  "}"
echo [stop-dev] Done.
