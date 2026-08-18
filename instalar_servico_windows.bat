@echo off
echo ============================================
echo INSTALANDO SERVICO WINDOWS - Refresh mv_geo3
echo ============================================
echo.

REM Verificar se NSSM existe
where nssm >nul 2>&1
if %errorlevel% neq 0 (
    echo NSSM nao encontrado. Baixando...
    echo.
    echo 1. Baixe o NSSM em: https://nssm.cc/download
    echo 2. Extraia e copie nssm.exe para C:\Windows\System32
    echo 3. Execute este script novamente
    echo.
    pause
    exit /b 1
)

REM Instalar servico
echo Instalando servico...
nssm install RefreshMvGeo3 "C:\Python312\python.exe" "c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_service.py"
nssm set RefreshMvGeo3 AppDirectory "c:\Users\ce_lu\OneDrive\Documentos\geo2"
nssm set RefreshMvGeo3 DisplayName "Refresh mv_geo3 - GeoVendas"
nssm set RefreshMvGeo3 Description "Atualiza a view materializada mv_geo3 a cada 2 horas"
nssm set RefreshMvGeo3 Start SERVICE_AUTO_START

echo.
echo Iniciando servico...
nssm start RefreshMvGeo3

echo.
echo ============================================
echo SERVICO INSTALADO COM SUCESSO!
echo ============================================
echo.
echo Comandos uteis:
echo   nssm status RefreshMvGeo3    - Ver status
echo   nssm stop RefreshMvGeo3      - Parar
echo   nssm start RefreshMvGeo3     - Iniciar
echo   nssm remove RefreshMvGeo3    - Remover
echo.
pause
