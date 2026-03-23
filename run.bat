@echo off
echo Iniciando sistema SGV Farma...
cd /d %~dp0

call venv\Scripts\activate

cd src
python app.py

pause