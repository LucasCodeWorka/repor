@echo off
title Refresh mv_cmv_loja_v2 -> mv_cmv_loja
echo ============================================
echo Atualizando mv_cmv_loja_v2, depois mv_cmv_loja...
echo ============================================
cd /d "c:\Users\ce_lu\OneDrive\Documentos\geo2"
C:\Python312\python.exe refresh_cmv_loja.py
echo.
echo Concluido. Fechando em 15 segundos...
timeout /t 15
