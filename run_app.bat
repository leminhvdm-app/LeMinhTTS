@echo off
cd /d "%~dp0"

:: Neu khong o che do an, tu dong kich hoat wscript chay ngam de dong ngay lap tuc cua so CMD
if "%1"=="--silent" goto :START_APP

echo Set WshShell = CreateObject("WScript.Shell") > "%temp%\leminh_run.vbs"
echo WshShell.Run """" ^& "%~f0" ^& """ --silent", 0, False >> "%temp%\leminh_run.vbs"
wscript "%temp%\leminh_run.vbs"
del "%temp%\leminh_run.vbs" 2>nul
exit /b

:START_APP
set PYTHONPATH=src;%PYTHONPATH%
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m vienetts_app
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m vienetts_app || start "" ".venv\Scripts\python.exe" -m vienetts_app
) else (
    start "" uv run vienetts-app
)
exit
