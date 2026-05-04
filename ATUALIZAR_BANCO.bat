@echo off
echo ============================================
echo   Agrobotic ScanBerry - Atualizar Banco
echo ============================================
echo.
echo Este script vai:
echo   1. Remover o banco de dados antigo
echo   2. Recriar com as novas tabelas (Usuarios)
echo   3. Criar admin padrao (WhatsApp: 0000 / Senha: admin123)
echo.
echo ATENCAO: Analises anteriores serao perdidas!
echo.
set /p CONFIRMA="Deseja continuar? (S/N): "
if /I not "%CONFIRMA%"=="S" (
    echo Operacao cancelada.
    pause
    exit /b
)
echo.
echo Removendo banco antigo...
cd /d "%~dp0"
if exist "instance\scanberry.db" (
    del /f "instance\scanberry.db"
    echo   Banco removido com sucesso.
) else (
    echo   Nenhum banco anterior encontrado.
)
echo.
echo Recriando banco de dados...
python init_db.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ FALHA NA ATUALIZACAO DO BANCO.
    echo Veja o erro acima e tente resolver as dependencias primeiro.
) else (
    echo.
    echo ============================================
    echo   Atualizacao concluida!
    echo   Execute INICIAR_SCANBERRY.bat para rodar
    echo ============================================
)
pause

