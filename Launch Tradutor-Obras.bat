@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py launch_tradutor_obras.py
) else (
    python launch_tradutor_obras.py
)

endlocal
