@echo off
setlocal EnableExtensions

if not defined APPDATA set "APPDATA=%USERPROFILE%\AppData\Roaming"
set "PID_FILE=%APPDATA%\OnPremImageGenerator\app.pid"

if not exist "%PID_FILE%" (
  echo No PID file found. Backend may not be running.
  exit /b 0
)

set /p PID=<"%PID_FILE%"
if defined PID (
  taskkill /PID %PID% /F >nul 2>&1
)

del "%PID_FILE%" >nul 2>&1
echo Backend stopped.
