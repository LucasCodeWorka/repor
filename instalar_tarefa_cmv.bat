@echo off
echo ============================================
echo INSTALANDO TAREFAS AGENDADAS - Refresh CMV
echo mv_cmv_loja_v2 -^> mv_cmv_loja -^> mv_cmv_fab
echo 06:00 e 17:00
echo ============================================

REM Remove tarefas antigas (nomes antigos e os separados), se existirem
schtasks /delete /tn "Refresh_mv_cmv_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_17h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_loja_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_loja_17h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_fab_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_fab_17h" /f >nul 2>&1

schtasks /create ^
    /tn "Refresh_mv_cmv_06h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv.bat\"" ^
    /sc daily ^
    /st 06:00 ^
    /f

schtasks /create ^
    /tn "Refresh_mv_cmv_17h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv.bat\"" ^
    /sc daily ^
    /st 17:00 ^
    /f

echo.
echo ============================================
echo TAREFAS INSTALADAS COM SUCESSO!
echo ============================================
echo.
echo Rodam todo dia as 06:00 e 17:00 (precisa estar logado), na ordem:
echo   1. mv_cmv_loja_v2, confere se populou, depois mv_cmv_loja
echo   2. mv_cmv_fab (incremental, janela de 10 dias)
echo.
echo Logs separados: refresh_cmv_loja.log e refresh_cmv_fab.log
echo.
echo Pra rodar so uma delas na mao:
echo   refresh_cmv_loja.bat   - so as views de loja
echo   refresh_cmv_fab.bat    - so a fabrica
echo.
echo Comandos uteis:
echo   schtasks /query /tn "Refresh_mv_cmv_06h"
echo   schtasks /run /tn "Refresh_mv_cmv_06h"        - Testar agora
echo   schtasks /delete /tn "Refresh_mv_cmv_06h" /f   - Remover
echo.
pause
