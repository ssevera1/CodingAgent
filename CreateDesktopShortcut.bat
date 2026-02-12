@echo off
echo Creating desktop shortcut...

set "SCRIPT_DIR=%~dp0"
set "SHORTCUT=%USERPROFILE%\Desktop\CodeAgent.lnk"
set "TARGET=%SCRIPT_DIR%CodeAgent.bat"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'CodeAgent - Offline Coding Agent'; $s.Save()"

if exist "%SHORTCUT%" (
    echo Done! "CodeAgent" shortcut created on your Desktop.
) else (
    echo Failed to create shortcut.
)
pause
