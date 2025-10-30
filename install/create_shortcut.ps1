param (
    [string]$ShortcutPath,
    [string]$TargetPath,
    [string]$Arguments,
    [string]$WorkingDir,
    [string]$IconPath,
    [int]$WindowStyle = 1
)

$WshShell = New-Object -ComObject WScript.Shell
# Validate shortcut path
if (-not (Test-Path (Split-Path $ShortcutPath))) {
    $DesktopFallback = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = "$DesktopFallback\NMS Dynamic Suit Voice.lnk"
}

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.Arguments = "`"$Arguments`""
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.WindowStyle = $WindowStyle
$Shortcut.Save()
