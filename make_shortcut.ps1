$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut("$env:USERPROFILE\Desktop\CodeAgent.lnk")
$shortcut.TargetPath = "$PSScriptRoot\CodeAgent.bat"
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "CodeAgent - Offline Coding Agent"
$shortcut.Save()
Write-Host "Desktop shortcut created!"
