@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting Price Monitor...
python monitor.py

pause
