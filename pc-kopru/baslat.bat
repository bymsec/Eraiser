@echo off
chcp 65001 >nul
title PC Koprusu
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js bulunamadi. Kurmak icin: winget install OpenJS.NodeJS.LTS
  pause
  exit /b 1
)

node kopru.js
pause
