@echo off
REM =====================================================================
REM stop-dev.bat
REM   Kill processes listening on port 8000 (uvicorn) and 5173 (vite).
REM   PowerShell is inlined directly; no external .ps1 file required.
REM   Note: $pid is a reserved variable in PowerShell, so $procId is used.
REM   Note: regex uses string concat to avoid double-quotes inside -Command.
REM =====================================================================

echo [stop-dev] Stopping development servers...

powershell -ExecutionPolicy Bypass -NoProfile -Command "$ports = @{8000 = 'backend (uvicorn)'; 5173 = 'frontend (vite)'}; foreach ($entry in $ports.GetEnumerator()) { $port = $entry.Key; $label = $entry.Value; $lines = netstat -ano | Select-String ('TCP\s+\S+:' + $port + '\s+\S+\s+LISTENING'); if ($lines) { $pids = $lines | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^\d+$' -and $_ -ne '0' } | Sort-Object -Unique; foreach ($procId in $pids) { $result = taskkill /F /T /PID $procId 2>&1; if ($LASTEXITCODE -eq 0) { Write-Host ('[stop-dev] Killed ' + $label + ' on port ' + $port + ' (PID=' + $procId + ')') } } } else { Write-Host ('[stop-dev] No process listening on port ' + $port + ' (' + $label + ')') } }"

echo [stop-dev] Done.
