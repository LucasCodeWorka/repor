@echo off
echo ============================================
echo INSTALANDO TAREFA AGENDADA - Refresh mv_vendas_qtd
echo ============================================

REM Remove tarefa antiga, se existir
schtasks /delete /tn "Refresh_mv_vendas_qtd" /f >nul 2>&1

REM Cria tarefa que roda a cada 2 horas (igual ao padrao do mv_geo3),
REM abrindo uma janela de cmd mostrando a atualizacao
schtasks /create ^
    /tn "Refresh_mv_vendas_qtd" ^
    /tr "\"c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_mv_vendas_qtd.bat\"" ^
    /sc hourly ^
    /mo 2 ^
    /f

echo.
echo ============================================
echo TAREFA INSTALADA COM SUCESSO!
echo ============================================
echo.
echo Roda a cada 2 horas (precisa estar logado), abrindo uma janela
echo de cmd mostrando a atualizacao.
echo.
echo Comandos uteis:
echo   schtasks /query /tn "Refresh_mv_vendas_qtd"
echo   schtasks /run /tn "Refresh_mv_vendas_qtd"        - Testar agora
echo   schtasks /delete /tn "Refresh_mv_vendas_qtd" /f   - Remover
echo.
pause
