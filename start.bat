@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0BowlBound.exe" (
    "%~dp0BowlBound.exe" %*
    exit /b
)
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m backend.launcher %*
) else (
    python -m backend.launcher %*
)
exit /b %errorlevel%
