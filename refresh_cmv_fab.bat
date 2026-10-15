@echo off
title Refresh mv_cmv_fab (isolado)
echo ============================================
echo Atualizando mv_cmv_fab (isolado)...
echo ============================================
cd /d "c:\Users\ce_lu\OneDrive\Documentos\geo2"
C:\Python312\python.exe refresh_cmv_fab.py
echo.
echo Concluido. Fechando em 15 segundos...
timeout /t 15
