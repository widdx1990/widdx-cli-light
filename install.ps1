# WIDDX Cortex — Smart Installer for PowerShell
# ==============================================
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
# أو انقر بزر الماوس الأيمن واختر "Run with PowerShell"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = "$env:USERPROFILE\.widdx\bin"
$VenvDir = "$ScriptDir\.venv"

# ── UI Helper ─────────────────────────────────────────────────
function Write-Step($emoji, $title) {
    Write-Host "`n  $emoji  $title" -ForegroundColor Cyan
    Write-Host "  " ("─" * 50) -ForegroundColor DarkGray
}

function Write-Success($msg) {
    Write-Host "  ✅ $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "  ⚠️  $msg" -ForegroundColor Yellow
}

function Write-Error($msg) {
    Write-Host "  ❌ $msg" -ForegroundColor Red
}

function Get-YesNo($prompt) {
    while ($true) {
        $input = Read-Host "  $prompt (Y/n)"
        if ($input -eq "" -or $input -eq "y" -or $input -eq "Y") { return $true }
        if ($input -eq "n" -or $input -eq "N") { return $false }
    }
}

# ── Header ──────────────────────────────────────────────────
Clear-Host
Write-Host @"
  ╔══════════════════════════════════════════════════════════╗
  ║      ◈  W I D D X   C O R T E X   v3.0  ◈            ║
  ║          مساعد البرمجة الذكي في الطرفية               ║
  ║                                                         ║
  ║     ~  Smart PowerShell Installer  ~                   ║
  ╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

# ── Step 1: Check Python ───────────────────────────────────
Write-Step "📋" "Step 1/5: فحص Python — Checking Python"

$pythonCmd = $null
foreach ($cmd in @("py", "python", "python3")) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $cmd
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Error "Python not found! Install Python 3.10+ from python.org"
    Write-Host "  🔗  https://www.python.org/downloads/" -ForegroundColor Blue
    Write-Host "`n  ⚠️  تأكد من تفعيل خيار 'Add Python to PATH' أثناء التثبيت"
    pause
    exit 1
}

$pyVersion = & $pythonCmd --version 2>&1
Write-Host "  Found: $pythonCmd → $pyVersion" -ForegroundColor White

# Parse version (e.g., "3.12.10")
$verParts = ($pyVersion -replace "Python ", "").Split(".")
if ([int]$verParts[0] -lt 3 -or ([int]$verParts[0] -eq 3 -and [int]$verParts[1] -lt 10)) {
    Write-Error "Python 3.10+ required. Found: $pyVersion"
    pause
    exit 1
}
Write-Success "Python version OK!"

# ── Step 2: Choose install method ──────────────────────────
Write-Step "📦" "Step 2/5: طريقة التثبيت — Install Method"

Write-Host @"
   [1] 🚀  تثبيت مباشر (مستوى النظام) — System-wide
           يثبت المكتبات في Python مباشرة (أسرع، الأفضل للمستخدمين العاديين)

   [2] 🛡️  بيئة افتراضية (معزولة) — Virtual Environment
           معزول عن بقية بايثون (آمن أكثر، الأفضل للمطورين)

"@
$method = Read-Host "  اختر (1 أو 2) — Choose (1 or 2) [default: 1]"
if ([string]::IsNullOrWhiteSpace($method)) { $method = "1" }

if ($method -eq "2") {
    Write-Host "  🛡️  Virtual environment selected" -ForegroundColor Yellow
} else {
    Write-Host "  🚀  System-wide install selected" -ForegroundColor Green
}

# ── Step 3: Install dependencies ───────────────────────────
Write-Step "📥" "Step 3/5: تثبيت المكتبات — Installing Dependencies"

if ($method -eq "2") {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    & $pythonCmd -m venv "$VenvDir"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        pause
        exit 1
    }
    $pipCmd = "$VenvDir\Scripts\pip.exe"
    $pythonCmd = "$VenvDir\Scripts\python.exe"
    Write-Success "Virtual environment created at $VenvDir"
} else {
    $pipCmd = "$pythonCmd -m pip"
}

Write-Host "  Upgrading pip..." -ForegroundColor Yellow
& $pythonCmd -m pip install --upgrade pip -q

Write-Host "  Installing WIDDX dependencies..." -ForegroundColor Yellow
Write-Host "  (This may take a few minutes...)" -ForegroundColor DarkGray

$reqPath = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $reqPath) {
    & $pythonCmd -m pip install -r $reqPath
} else {
    & $pythonCmd -m pip install -e $ScriptDir
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies!"
    Write-Warn "You may need Visual Studio Build Tools for C++ from:"
    Write-Host "  🔗  https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Blue
    pause
    exit 1
}
Write-Success "Dependencies installed!"

# ── Step 4: Create launchers ───────────────────────────────
Write-Step "🚀" "Step 4/5: إنشاء مشغّلات — Creating Launchers"

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
}

# Determine embedded Python path
if ($method -eq "2") {
    $embeddedPython = "$VenvDir\Scripts\python.exe"
} else {
    $embeddedPython = "python"
}

# Calculate relative paths for the launcher
$relativeScriptDir = $ScriptDir -replace '\\', '\\'

# Create widdx.bat (CLI)
$widdxBat = @"
@echo off
REM WIDDX Cortex — CLI Launcher
REM Generated by install.ps1
set "WIDDX_ROOT=$relativeScriptDir"
"$embeddedPython" "%WIDDX_ROOT%\main.py" %*
"@
[System.IO.File]::WriteAllText("$BinDir\widdx.bat", $widdxBat.Trim(), [System.Text.Encoding]::ASCII)
Write-Success "Created widdx.bat (CLI)"

# Create widdx-tui.bat (TUI)
$widdxTuiBat = @"
@echo off
REM WIDDX Cortex — TUI Launcher
REM Generated by install.ps1
set "WIDDX_ROOT=$relativeScriptDir"
"$embeddedPython" "%WIDDX_ROOT%\run_textual.py" %*
"@
[System.IO.File]::WriteAllText("$BinDir\widdx-tui.bat", $widdxTuiBat.Trim(), [System.Text.Encoding]::ASCII)
Write-Success "Created widdx-tui.bat (TUI)"

# ── Step 5: Add to PATH ──────────────────────────────────
Write-Step "🔗" "Step 5/5: إضافة إلى PATH — Adding to PATH"

$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$BinDir*") {
    $newPath = "$currentPath;$BinDir"
    try {
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        $env:PATH = "$env:PATH;$BinDir"
        Write-Success "Added to PATH!"
    } catch {
        Write-Warn "Could not add to PATH automatically"
        Write-Host "  Add this to your PATH manually: $BinDir" -ForegroundColor Yellow
    }
} else {
    Write-Success "Already in PATH!"
}

# ── Desktop shortcut (optional) ───────────────────────────
Write-Step "🖥️" "Bonus: اختصار سطح المكتب — Desktop Shortcut"

if (Get-YesNo "هل تريد إنشاء اختصار على سطح المكتب؟") {
    try {
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\WIDDX Cortex.lnk")
        $sc.TargetPath = "$BinDir\widdx-tui.bat"
        $sc.WorkingDirectory = $env:USERPROFILE
        $sc.Description = "WIDDX Cortex — Terminal AI Assistant"
        $sc.Save()
        Write-Success "Desktop shortcut created!"
    } catch {
        Write-Warn "Could not create shortcut. You can create it manually."
    }
}

# ── Complete! ─────────────────────────────────────────────
Clear-Host
Write-Host @"
  ╔══════════════════════════════════════════════════════════╗
  ║                                                        ║
  ║    🎉  ◈  W I D D X  C O R T E X  ◈  🎉              ║
  ║                                                        ║
  ║         ✅  تم التثبيت بنجاح!                         ║
  ║         ✅  Installation Complete!                    ║
  ║                                                        ║
  ╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

Write-Host @"

  📌 Installation Summary:
  ─────────────────────────
  Install dir:  $ScriptDir
  Launchers:    $BinDir

  🎯 How to use:
  ─────────────────────────
  ▶️  widdx              CLI mode (النصية)
  ▶️  widdx-tui          TUI mode ★ (المحسنة)

  ❓  Type /help inside WIDDX for commands

"@ -ForegroundColor White

Write-Host "  ⚠️  Important: Restart your terminal, then try: widdx-tui" -ForegroundColor Yellow
Write-Host @"

  💡  Enjoy smart coding with WIDDX! 😊

"@ -ForegroundColor Green

pause
