@echo off
setlocal EnableExtensions

set "HOST=127.0.0.1"
set "PORT=8000"
set "URL=http://%HOST%:%PORT%"
set "HEALTH=%URL%/api/health"
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"

if not defined APPDATA set "APPDATA=%USERPROFILE%\AppData\Roaming"
set "PID_FILE=%APPDATA%\OnPremImageGenerator\app.pid"

where curl >nul 2>&1
if errorlevel 1 (
  echo curl is required for health checks. Install curl or open %URL% manually after starting the backend.
)

curl -fs "%HEALTH%" >nul 2>&1
if not errorlevel 1 (
  start "" "%URL%"
  exit /b 0
)

pushd "%BACKEND%"
start "" /B pythonw -m uvicorn app.main:app --host %HOST% --port %PORT% >nul 2>&1
popd

set /a ATTEMPTS=0
:wait_loop
curl -fs "%HEALTH%" >nul 2>&1
if not errorlevel 1 goto ready
set /a ATTEMPTS+=1
if %ATTEMPTS% GEQ 60 (
  echo Backend did not start within 30 seconds.
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_loop

:ready
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq pythonw.exe" /fo list ^| find "PID:"') do set "LAST_PID=%%a"
if defined LAST_PID echo %LAST_PID%>"%PID_FILE%"
start "" "%URL%"
exit /b 0
