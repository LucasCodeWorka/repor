@echo off
echo ============================================
echo INSTALANDO TAREFAS AGENDADAS (separadas)
echo Refresh_mv_cmv_loja: mv_cmv_loja_v2 -^> mv_cmv_loja - 06:00 e 17:00
echo Refresh_mv_cmv_fab : mv_cmv_fab (incremental)       - 06:30 e 17:30
echo ============================================

REM Remove tarefas antigas (nome unico antigo e os novos, se ja existirem)
schtasks /delete /tn "Refresh_mv_cmv_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_17h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_loja_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_loja_17h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_fab_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_fab_17h" /f >nul 2>&1

REM --- mv_cmv_loja_v2 -> mv_cmv_loja (06:00 e 17:00) ---
schtasks /create ^
    /tn "Refresh_mv_cmv_loja_06h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv_loja.bat\"" ^
    /sc daily ^
    /st 06:00 ^
    /f

schtasks /create ^
    /tn "Refresh_mv_cmv_loja_17h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv_loja.bat\"" ^
    /sc daily ^
    /st 17:00 ^
    /f

REM --- mv_cmv_fab, incremental e isolada (06:30 e 17:30) ---
REM Meia hora depois da loja, pra nao competirem por recurso no servidor.
schtasks /create ^
    /tn "Refresh_mv_cmv_fab_06h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv_fab.bat\"" ^
    /sc daily ^
    /st 06:30 ^
    /f

schtasks /create ^
    /tn "Refresh_mv_cmv_fab_17h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv_fab.bat\"" ^
    /sc daily ^
    /st 17:30 ^
    /f

echo.
echo ============================================
echo TAREFAS INSTALADAS COM SUCESSO!
echo ============================================
echo.
echo Rodam todo dia as 06:00 e 17:00, cada uma na sua janela de cmd
echo (precisa estar logado). mv_cmv_loja e mv_cmv_fab agora sao
echo totalmente independentes -- uma nao trava nem afeta a outra.
echo.
echo Comandos uteis:
echo   schtasks /query /tn "Refresh_mv_cmv_loja_06h"
echo   schtasks /query /tn "Refresh_mv_cmv_fab_06h"
echo   schtasks /run /tn "Refresh_mv_cmv_loja_06h"    - Testar loja agora
echo   schtasks /run /tn "Refresh_mv_cmv_fab_06h"     - Testar fab agora
echo.
pause
