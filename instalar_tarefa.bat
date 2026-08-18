@echo off
echo ============================================
echo INSTALANDO TAREFA AGENDADA - Refresh mv_geo3
echo ============================================

REM Criar tarefa que roda a cada 2 horas
schtasks /create /tn "Refresh_mv_geo3" /tr "python c:\Users\ce_lu\OneDrive\Documentos\geo2\refresh_unico.py" /sc hourly /mo 2 /f

echo.
echo Tarefa criada! Para verificar:
echo   schtasks /query /tn "Refresh_mv_geo3"
echo.
echo Para remover:
echo   schtasks /delete /tn "Refresh_mv_geo3" /f
echo.
pause
