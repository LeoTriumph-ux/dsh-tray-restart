@echo off
chcp 65001 >nul
setlocal
title DeepSeek Harness - tray restart patch
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
