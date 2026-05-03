Option Explicit

Dim fso, shell, scriptDir, projectDir, parentDir
Dim pywCandidates(2), pywPath, i
Dim cmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = scriptDir
parentDir = fso.GetParentFolderName(projectDir)

pywCandidates(0) = projectDir & "\\.venv\\Scripts\\pythonw.exe"
pywCandidates(1) = parentDir & "\\.venv\\Scripts\\pythonw.exe"
pywCandidates(2) = "pythonw.exe"

pywPath = ""
For i = 0 To 2
    If i = 2 Then
        pywPath = pywCandidates(i)
        Exit For
    End If
    If fso.FileExists(pywCandidates(i)) Then
        pywPath = pywCandidates(i)
        Exit For
    End If
Next

cmd = "cmd /c cd /d """ & projectDir & """ && """ & pywPath & """ ""gui_app.py"""

shell.Run cmd, 0, False
