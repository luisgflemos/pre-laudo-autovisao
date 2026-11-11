@echo off
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
 "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" inspecionar_api_erpflex.py
) else (
 py inspecionar_api_erpflex.py
)
