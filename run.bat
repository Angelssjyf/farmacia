@echo off
title SGV FARMA

echo ============================
echo INICIANDO SGV FARMA...
echo ============================

cd /d %~dp0

:: activar entorno virtual
call venv\Scripts\activate

:: abrir flask en otra ventana
start cmd /k "cd src && python app.py"

:: esperar unos segundos
timeout /t 5

:: abrir ngrok
start cmd /k "ngrok http 5000"

echo.
echo Sistema iniciado correctamente
pause