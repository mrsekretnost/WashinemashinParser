Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Запуск python monitor.py в полностью скрытом окне (0 = без консоли)
WshShell.Run "python """ & currentDir & "\monitor.py""", 0, False
