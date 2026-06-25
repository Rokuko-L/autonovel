Set ws = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ws.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
ws.Run "uv run python gui.py", 0, False
