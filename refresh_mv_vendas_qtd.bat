@echo off
title Refresh mv_vendas_qtd
echo ============================================
echo Atualizando mv_vendas_qtd (ultimos 10 dias)...
echo ============================================
cd /d "c:\Users\ce_lu\OneDrive\Documentos\geo2"
C:\Python312\python.exe refresh_mv_vendas_qtd.py
echo.
echo Concluido. Fechando em 15 segundos...
timeout /t 15
