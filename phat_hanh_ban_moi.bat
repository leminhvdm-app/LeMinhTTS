@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Khong tim thay Python tai .venv\Scripts\python.exe!
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "scripts\publish_release.py" %*

pause
