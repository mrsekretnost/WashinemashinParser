Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Запуск start.bat в скрытом окне (0 = скрыть терминал)
WshShell.Run """" & currentDir & "\start.bat""", 0, False
