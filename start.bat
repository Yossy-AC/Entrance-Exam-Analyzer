@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "HOST=127.0.0.1"
set "PORT=8000"
set "APP=src.goukaku_analytics.main:app"
set "PROJECT_DIR=%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

cd /d "%PROJECT_DIR%"

set "PORT_PID="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "Get-NetTCPConnection -LocalAddress '%HOST%' -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess"`) do (
  set "PORT_PID=%%P"
)

if defined PORT_PID goto :CHECK_PORT_OWNER
goto :START_SERVER

:CHECK_PORT_OWNER
set "CMDLINE="
for /f "usebackq delims=" %%C in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object ProcessId -eq %PORT_PID% | Select-Object -ExpandProperty CommandLine"`) do (
  set "CMDLINE=%%C"
)

if not defined CMDLINE (
  echo [ERROR] Port %PORT% is in use. PID=%PORT_PID%. Process details were unavailable.
  echo [ERROR] Stop that process manually and run start.bat again.
  exit /b 1
)

echo [INFO] Port %PORT% is already in use by PID %PORT_PID%.
echo [INFO] CommandLine: !CMDLINE!

echo !CMDLINE! | findstr /I /C:"uvicorn" >nul
if errorlevel 1 (
  echo [ERROR] The process is not uvicorn. Auto-stop is skipped.
  exit /b 1
)

echo !CMDLINE! | findstr /I /C:"%APP%" >nul
if errorlevel 1 (
  echo [ERROR] Uvicorn does not match this app module. Auto-stop is skipped.
  exit /b 1
)

echo [INFO] Stopping existing project uvicorn...
taskkill /PID %PORT_PID% /T /F >nul 2>&1
timeout /t 1 /nobreak >nul

:START_SERVER
chcp 65001 > nul
echo Starting dashboard...
echo Open http://localhost:%PORT% in your browser
echo Press Ctrl+C to stop
echo.
uv run uvicorn %APP% --host %HOST% --port %PORT% --reload
