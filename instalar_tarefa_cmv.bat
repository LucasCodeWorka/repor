i@echo off
echo ============================================
echo INSTALANDO TAREFAS AGENDADAS
echo Refresh mv_cmv_loja_v2 / mv_cmv_fab - 06:00 e 17:00
echo ============================================

REM Remove tarefas antigas, se existirem
schtasks /delete /tn "Refresh_mv_cmv_06h" /f >nul 2>&1
schtasks /delete /tn "Refresh_mv_cmv_17h" /f >nul 2>&1

REM Cria tarefa das 06:00 (abre janela do cmd mostrando o progresso)
schtasks /create ^
    /tn "Refresh_mv_cmv_06h" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_cmv.bat\"" ^
    /sc daily ^
    /st 06:00 ^
    /f

REM Cria tarefa das 17:00 (abre janela do cmd mostrando o progresso)
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
echo Rodam todo dia as 06:00 e 17:00, abrindo uma janela
echo de cmd mostrando a atualizacao (precisa estar logado).
echo.
echo Comandos uteis:
echo   schtasks /query /tn "Refresh_mv_cmv_06h"
echo   schtasks /query /tn "Refresh_mv_cmv_17h"
echo   schtasks /run /tn "Refresh_mv_cmv_06h"        - Testar agora
echo   schtasks /delete /tn "Refresh_mv_cmv_06h" /f   - Remover
echo   schtasks /delete /tn "Refresh_mv_cmv_17h" /f   - Remover
echo.
pause
