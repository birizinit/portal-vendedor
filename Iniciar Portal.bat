@echo off
title Portal de Inteligencia de Carteira
echo Iniciando Portal de Inteligencia de Carteira...
echo.

cd /d "%~dp0backend"
start "Portal - Backend (8001)" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001"

cd /d "%~dp0frontend"
start "Portal - Frontend (5173)" cmd /k "npm run dev"

echo Aguardando subir os servidores...
timeout /t 5 >nul
start http://localhost:5173
echo.
echo Pronto! Abra http://localhost:5173 no navegador.
echo (Backend: http://127.0.0.1:8001  ^|  Docs da API: http://127.0.0.1:8001/docs)
