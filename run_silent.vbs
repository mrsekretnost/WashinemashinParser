Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Запуск streamlit в полностью скрытом режиме (0 = окно терминала вообще не появляется)
WshShell.Run "python -m streamlit run """ & currentDir & "\app.py"" --server.headless=false --browser.gatherUsageStats=false", 0, False
