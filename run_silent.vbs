Set WshShell = CreateObject("WScript.Shell")
' Запуск streamlit в полностью скрытом режиме (0 = окно скрыто)
WshShell.Run "python -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false", 0, False
