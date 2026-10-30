@echo off
chcp 65001 >nul
title Установка и подготовка парсера стиральных машин
cd /d "%~dp0"

echo =====================================================================
echo    Первоначальная автоматическая настройка приложения
echo =====================================================================
echo.

:: 1. Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не обнаружен!
    echo Пожалуйста, установите Python с официального сайта: https://www.python.org/
    echo Обязательно отметьте галочку "Add Python to PATH" при установке!
    pause
    exit /b
)

:: 2. Настраиваем конфиг Streamlit чтобы не спрашивал Email
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
(
echo [general]
echo email = ""
) > "%USERPROFILE%\.streamlit\credentials.toml"

(
echo [browser]
echo gatherUsageStats = false
echo [server]
echo headless = false
) > "%USERPROFILE%\.streamlit\config.toml"

:: 3. Устанавливаем зависимости
echo [1/3] Установка библиотек из requirements.txt...
pip install -r requirements.txt --quiet --disable-pip-version-check

:: 4. Устанавливаем браузер Chromium для работы антибот-парсинга
echo [2/3] Загрузка Chromium движка для обхода защит магазинов...
python -m playwright install chromium

:: 5. Создаем ярлыки на рабочем столе
echo [3/3] Создание ярлыков на Рабочем столе...
python -c "
import winreg, os
try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
    desktop, _ = winreg.QueryValueEx(key, 'Desktop')
    desktop = os.path.expandvars(desktop)
    
    cur_dir = os.path.abspath('.')
    vbs = f'''
    Set oWS = WScript.CreateObject(\"WScript.Shell\")
    sLink = \"{desktop}\\\\Washers_Georgievsk.lnk\"
    Set oLink = oWS.CreateShortcut(sLink)
    oLink.TargetPath = \"wscript.exe\"
    oLink.Arguments = \"\\\"{cur_dir}\\\\run_silent.vbs\\\"\"
    oLink.WorkingDirectory = \"{cur_dir}\"
    oLink.Description = \"Стиральные машины Георгиевск\"
    oLink.IconLocation = \"shell32.dll,13\"
    oLink.Save

    sLink2 = \"{desktop}\\\\Price_Monitor_Georgievsk.lnk\"
    Set oLink2 = oWS.CreateShortcut(sLink2)
    oLink2.TargetPath = \"{cur_dir}\\\\start_monitor.bat\"
    oLink2.WorkingDirectory = \"{cur_dir}\"
    oLink2.Description = \"Мониторинг цен Георгиевск\"
    oLink2.IconLocation = \"shell32.dll,175\"
    oLink2.Save
    '''
    with open('create_temp.vbs', 'w', encoding='cp1251') as f:
        f.write(vbs)
    os.system('cscript //nologo create_temp.vbs')
    if os.path.exists('create_temp.vbs'):
        os.remove('create_temp.vbs')
    print('Ярлыки успешно созданы на Рабочем столе!')
except Exception as e:
    print('Ошибка создания ярлыка:', e)
"

echo.
echo =====================================================================
echo    Настройка успешно завершена!
echo    Теперь вы можете запускать программу через:
echo    1) Ярлык на Рабочем столе: Washers_Georgievsk.lnk
echo    2) Или файл: start.bat
echo =====================================================================
echo.
pause
