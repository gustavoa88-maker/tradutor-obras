@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher ^(py^) nao foi encontrado.
    echo Instale Python 3.12 e tente novamente.
    pause
    exit /b 1
)

py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 nao foi encontrado.
    echo Instale com: winget install -e --id Python.Python.3.12
    pause
    exit /b 1
)

py -3.12 launch_tradutor_obras.py

endlocal
