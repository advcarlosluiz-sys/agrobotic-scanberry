@echo off
echo ============================================
echo   Agrobotic ScanBerry - Servidor Local
echo ============================================
echo.
echo Iniciando servidor em http://localhost:5000
echo Pressione Ctrl+C para parar
echo.
cd /d "%~dp0"
python app.py
pause
