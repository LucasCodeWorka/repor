@echo off
echo ============================================
echo INSTALANDO TAREFA AGENDADA - Refresh mv_geo3
echo ============================================
echo.

REM Remover tarefa existente se houver
schtasks /delete /tn "RefreshMvGeo3" /f >nul 2>&1

REM Criar tarefa que roda a cada 2 horas, mesmo sem usuario logado
schtasks /create ^
    /tn "RefreshMvGeo3" ^
    /tr "C:\Python312\python.exe c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_unico.py" ^
    /sc hourly ^
    /mo 2 ^
    /ru SYSTEM ^
    /rl HIGHEST ^
    /f

echo.
echo ============================================
echo TAREFA INSTALADA COM SUCESSO!
echo ============================================
echo.
echo A tarefa roda a cada 2 horas, mesmo sem usuario logado.
echo.
echo Comandos uteis:
echo   schtasks /query /tn "RefreshMvGeo3"           - Ver status
echo   schtasks /run /tn "RefreshMvGeo3"             - Executar agora
echo   schtasks /end /tn "RefreshMvGeo3"             - Parar
echo   schtasks /delete /tn "RefreshMvGeo3" /f       - Remover
echo.
pause
