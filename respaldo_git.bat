@echo off
cd /d C:\xampp\htdocs\farmacia

echo ================================
echo   GUARDANDO Y SUBIENDO CAMBIOS
echo ================================

:: Obtener fecha y hora para el commit
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do (
    set fecha=%%a-%%b-%%c
)

:: Agregar y subir cambios automáticamente
git add .
git commit -m "Respaldo automático %fecha%"
git push

echo.
echo ✅ Respaldo completado correctamente.
echo.
pause
