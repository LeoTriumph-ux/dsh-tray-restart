@echo off
chcp 65001 >nul
setlocal
title DeepSeek Harness - restore tray menu
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
