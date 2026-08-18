@echo off
cd /d "%~dp0"
C:\Python312\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
