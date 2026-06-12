# WIDDX Uninstaller — removes `widdx` command from your system
# Run: powershell -ExecutionPolicy Bypass -File uninstall.ps1

$BinDir = "$env:USERPROFILE\.widdx"

# Remove from PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentPath -like "*$BinDir*") {
    $NewPath = ($CurrentPath -split ";" | Where-Object { $_ -ne $BinDir }) -join ";"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Host "✅ Removed $BinDir from PATH" -ForegroundColor Green
}

# Remove files
if (Test-Path $BinDir) {
    Remove-Item -Recurse -Force $BinDir
    Write-Host "✅ Removed $BinDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "👋 WIDDX uninstalled. Restart your terminal for changes to take effect."
