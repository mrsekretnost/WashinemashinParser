@echo off
cd /d "%~dp0"

python init_setup.py
python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

if %errorlevel% neq 0 (
    pause
)
