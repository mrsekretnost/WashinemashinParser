@echo off
cd /d "%~dp0"

python init_setup.py
python monitor.py
pause
