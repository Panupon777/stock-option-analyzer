@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>&1
if errorlevel 1 goto docker_missing
if not exist ".env" goto env_missing
docker info >nul 2>&1
if not errorlevel 1 goto start_services
if not exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" goto docker_missing
echo Starting Docker Desktop...
powershell.exe -NoProfile -Command "Start-Process -FilePath ($env:ProgramFiles + '\Docker\Docker\Docker Desktop.exe') -WindowStyle Hidden"
set /a attempts=0
:wait_docker
docker info >nul 2>&1
if not errorlevel 1 goto start_services
set /a attempts+=1
if %attempts% geq 60 goto docker_timeout
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 3"
goto wait_docker

:start_services
echo Starting Stock Analyzer services...
docker compose up -d
if errorlevel 1 goto startup_failed
echo Waiting for the website and API...
set /a attempts=0
:wait_web
curl.exe --fail --silent --max-time 5 --output NUL http://localhost:8000/health
if errorlevel 1 goto retry_web
curl.exe --fail --silent --max-time 5 --output NUL http://localhost:3000
if not errorlevel 1 goto open_apps
:retry_web
set /a attempts+=1
if %attempts% geq 60 goto web_timeout
powershell.exe -NoProfile -Command "Start-Sleep -Seconds 2"
goto wait_web

:open_apps
start "" "http://localhost:3000"
if exist "%ProgramFiles%\DBeaver\dbeaver.exe" (
  start "" "%ProgramFiles%\DBeaver\dbeaver.exe"
) else (
  echo DBeaver was not found. The website is ready.
  pause
)
echo Ready: http://localhost:3000
exit /b 0

:docker_missing
echo ERROR: Docker Desktop was not found. Install it or check PATH.
goto failure
:env_missing
echo ERROR: The project .env file is missing.
goto failure
:docker_timeout
echo ERROR: Docker Desktop is not ready. Open it and try again.
goto failure
:web_timeout
echo ERROR: Services are not ready. Check docker compose logs.
goto failure
:startup_failed
echo ERROR: Docker Compose could not start the project.
:failure
pause
exit /b 1
