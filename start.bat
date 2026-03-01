@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "HOST=127.0.0.1"
set "BASE_PORT=8000"
set "MAX_PORT=8010"
set "APP=src.goukaku_analytics.main:app"
set "PROJECT_DIR=%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
set "RELOAD_FLAG="
set "RUN_PORT="

if /I "%~1"=="--reload" set "RELOAD_FLAG=--reload"

cd /d "%PROJECT_DIR%"

echo [INFO] Cleaning old app processes...
powershell -NoProfile -Command ^
  "$hostIp = '%HOST%'; $start = %BASE_PORT%; $last = %MAX_PORT%; " ^
  "$appProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -match 'src\.goukaku_analytics\.main:app' -and $_.CommandLine -match 'uvicorn' }; " ^
  "foreach($p in $appProcs){ try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }; " ^
  "$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -eq $hostIp -and $_.LocalPort -ge $start -and $_.LocalPort -le $last }; " ^
  "$pids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique); " ^
  "foreach($pid in $pids){ try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}; " ^
  "$children = Get-CimInstance Win32_Process -Filter ('ParentProcessId=' + $pid) -ErrorAction SilentlyContinue; foreach($c in $children){ try { Stop-Process -Id $c.ProcessId -Force -ErrorAction SilentlyContinue } catch {} } }"

:: Wait for OS to release ports after killing processes
echo [INFO] Waiting for port release...
timeout /t 2 /nobreak > nul

for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$start=%BASE_PORT%; $last=%MAX_PORT%; for($p=$start; $p -le $last; $p++){ if(-not (Get-NetTCPConnection -LocalAddress '%HOST%' -LocalPort $p -State Listen -ErrorAction SilentlyContinue)){ $p; exit 0 } }; exit 1"`) do (
  set "RUN_PORT=%%P"
)

if not defined RUN_PORT (
  echo [ERROR] No free port found between %BASE_PORT% and %MAX_PORT%.
  netstat -ano | findstr ":80"
  exit /b 1
)

if not "%RUN_PORT%"=="%BASE_PORT%" (
  echo [WARN] Port %BASE_PORT% is busy. Using port %RUN_PORT% instead.
)

chcp 65001 > nul
echo Starting dashboard...
echo Open http://localhost:%RUN_PORT% in your browser
echo Press Ctrl+C to stop
if defined RELOAD_FLAG (
  echo Reload mode: ON
) else (
  echo Reload mode: OFF
)
echo.

uv run uvicorn %APP% --host %HOST% --port %RUN_PORT% %RELOAD_FLAG%
