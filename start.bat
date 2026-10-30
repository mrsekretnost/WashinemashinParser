@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting Washer Parser UI...
python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

pause
