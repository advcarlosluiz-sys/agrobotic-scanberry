@echo off
echo ============================================
echo   Agrobotic ScanBerry - Instalacao
echo ============================================
echo.
echo Instalando dependencias Python a partir do requirements.txt...
pip install -r requirements.txt
echo.
if %errorlevel% neq 0 (
    echo.
    echo ❌ Ocorreu um erro na instalacao das dependencias.
    echo Verifique sua conexao com a internet e se o Python/Pip estao no PATH.
) else (
    echo.
    echo ✅ Instalacao concluida com sucesso!
)
echo.
pause
