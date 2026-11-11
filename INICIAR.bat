@echo off
setlocal
cd /d "%~dp0"
title Pre-Laudo Vision
echo.
echo ================================================
echo  PRE-LAUDO VISION - INICIALIZACAO
echo ================================================
echo.
where py >nul 2>nul
if not errorlevel 1 goto usar_py
where python >nul 2>nul
if not errorlevel 1 goto usar_python
echo Python nao encontrado. Instale Python 3 e tente novamente.
pause
exit /b 1

:usar_py
py iniciar.py %*
goto resultado

:usar_python
python iniciar.py %*

:resultado
if errorlevel 1 goto falha
exit /b 0

:falha
echo.
echo Nao foi possivel concluir a inicializacao. Veja a mensagem acima.
pause
exit /b 1
