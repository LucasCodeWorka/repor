@echo off
title Refresh CMV (loja + fab)
cd /d "c:\Users\ce_lu\OneDrive\Documentos\geo2"

echo ============================================
echo 1/2 - mv_cmv_loja_v2, depois mv_cmv_loja...
echo ============================================
C:\Python312\python.exe refresh_cmv_loja.py

echo.
echo ============================================
echo 2/2 - mv_cmv_fab (incremental)...
echo ============================================
C:\Python312\python.exe refresh_cmv_fab.py

echo.
echo Concluido. Fechando em 15 segundos...
timeout /t 15
