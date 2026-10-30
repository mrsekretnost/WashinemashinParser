@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 1. Проверяем, установлены ли библиотеки
python -c "import streamlit, playwright, pandas, openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ИНФО] Первичный запуск на новом компьютере. Запуск быстрой автонастройки...
    call setup.bat
)

:: 2. Создаем конфиг Streamlit чтобы не спрашивал Email если его еще нет
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    (
    echo [general]
    echo email = ""
    ) > "%USERPROFILE%\.streamlit\credentials.toml"
)

:: 3. Запуск веб-приложения
echo Запуск приложения в браузере...
python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

if %errorlevel% neq 0 (
    echo.
    echo Ошибка при запуске. Нажмите любую клавишу для выхода...
    pause
)
