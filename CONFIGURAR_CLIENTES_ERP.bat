@echo off
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" (
 start "" "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" configurar_clientes_erp.py
) else (
 py configurar_clientes_erp.py
)
