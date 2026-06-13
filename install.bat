@echo off
REM ============================================================================
REM  WIDDX Cortex — Easy Installer (Double-click to install!)
REM  للمستخدمين العاديين والمحترفين — فقط اضغط مرتين واتبع التعليمات
REM ============================================================================
chcp 65001 >nul
setlocal enabledelayedexpansion

set "WIDDX_DIR=%~dp0"
set "WIDDX_DIR=%WIDDX_DIR:~0,-1%"
set "BIN_DIR=%USERPROFILE%\.widdx\bin"
set "VENV_DIR=%WIDDX_DIR%\.venv"

:: ── عنوان الترحيب ───────────────────────────────────────────
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║      ◈  W I D D X   C O R T E X   v3.0  ◈            ║
echo   ║          مساعد البرمجة الذكي في الطرفية               ║
echo   ║                                                         ║
echo   ║     ~  تثبيت بنقرة واحدة  ~                           ║
echo   ║          One-Click Installer                          ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   هذا المثبت سيقوم بتثبيت WIDDX تلقائيًا على جهازك
echo   This installer will set up WIDDX automatically
echo.

:: ── التحقق من صلاحيات المسؤول ───────────────────────────────
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [!] تمارين: يفضل تشغيل المثبت كمسؤول (Administrator)
    echo   [!] Note: Running as Administrator is recommended
    echo   [!] للمتابعة بدون صلاحيات المسؤول، اضغط أي مفتاح...
    echo.
    pause >nul
)

:: ── 1. فحص Python ──────────────────────────────────────────
:check_python
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║    📋  1/5  فحص Python — Checking Python              ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.

:: Search for Python in order: py, python, python3
set "PYTHON_CMD="
for %%c in (py python python3) do (
    where %%c >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_CMD=%%c"
        goto :found_python
    )
)

:found_python
if "%PYTHON_CMD%"=="" (
    echo   ❌ لم يتم العثور على Python!
    echo   ❌ Python not found!
    echo.
    echo   ⚠️  قم بتثبيت Python 3.10 أو أحدث من
    echo   ⚠️  Install Python 3.10+ from:
    echo   🔗  https://www.python.org/downloads/
    echo.
    echo   ⚠️  تأكد من تفعيل خيار "Add Python to PATH" أثناء التثبيت
    echo   ⚠️  Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

:: Check Python version
for /f "tokens=2" %%v in ('"%PYTHON_CMD%" --version 2^>nul') do set "PY_VER=%%v"
echo   ✅ تم العثور على Python — Found Python: %PYTHON_CMD%
echo   📌 الإصدار — Version: %PY_VER%
echo.

:: Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do set "PY_MAJOR=%%a" & set "PY_MINOR=%%b"

if %PY_MAJOR% LSS 3 (
    echo   ❌ الإصدار قديم — Python 3.10+ مطلوب
    echo   ❌ Python 3.10+ required
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo   ❌ الإصدار قديم — Python 3.10+ مطلوب
    echo   ❌ Python 3.10+ required
    pause
    exit /b 1
)

echo   ✅ الإصدار مدعوم — Version is supported!
timeout /t 2 >nul

:: ── 2. اختيار طريقة التثبيت ──────────────────────────────
:install_method
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║    📦  2/5  اختيار طريقة التثبيت — Install Method     ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   اختر طريقة التثبيت — Choose installation method:
echo.
echo   [1] 🚀  تثبيت سريع (مباشر في النظام) — System-wide install
echo            يثبت المكتبات مباشرة في Python (أسرع)
echo            Recommended for most users
echo.
echo   [2] 🛡️  تثبيت في بيئة افتراضية (Virtual Environment)
echo            معزول عن بقية بايثون (آمن أكثر)
echo            Recommended for developers
echo.
set /p "METHOD=اختر (1 أو 2) — Choose (1 or 2) [1]: "
if "%METHOD%"=="" set "METHOD=1"

:: ── 3. تثبيت التبعيات ─────────────────────────────────────
:install_deps
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║    📥  3/5  تثبيت المكتبات — Installing Dependencies   ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.

if "%METHOD%"=="2" (
    echo   🛡️  إنشاء بيئة افتراضية — Creating virtual environment...
    "%PYTHON_CMD%" -m venv "%VENV_DIR%"
    if !ERRORLEVEL! NEQ 0 (
        echo   ❌ فشل إنشاء البيئة الافتراضية
        pause
        exit /b 1
    )
    echo   ✅ تم إنشاء البيئة الافتراضية بنجاح!
    set "PIP_CMD=%VENV_DIR%\Scripts\pip.exe"
    set "PYTHON_CMD=%VENV_DIR%\Scripts\python.exe"
) else (
    echo   🚀  تثبيت مباشر في النظام — System-wide install
    set "PIP_CMD=%PYTHON_CMD% -m pip"
)

:: Upgrade pip first
echo.
echo   ⬆️  تحديث pip — Upgrading pip...
"%PYTHON_CMD%" -m pip install --upgrade pip -q
if !ERRORLEVEL! NEQ 0 (
    echo   ⚠️  فشل تحديث pip (غير حرج) — Continuing anyway...
)

:: Install from requirements.txt
echo.
echo   📦  تثبيت المكتبات — Installing packages...
echo   هذا قد يستغرق بضع دقائق — This may take a few minutes...
echo.

if exist "%WIDDX_DIR%\requirements.txt" (
    "%PYTHON_CMD%" -m pip install -r "%WIDDX_DIR%\requirements.txt"
) else (
    "%PYTHON_CMD%" -m pip install -e "%WIDDX_DIR%"
)

if !ERRORLEVEL! NEQ 0 (
    echo.
    echo   ❌ فشل تثبيت بعض المكتبات
    echo   ❌ Failed to install some dependencies
    echo.
    echo   ⚠️  قد تحتاج إلى تثبيت Visual Studio Build Tools لـ C++
    echo   ⚠️  من: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    pause
    exit /b 1
)

echo   ✅ تم تثبيت جميع المكتبات بنجاح!
timeout /t 2 >nul

:: ── 4. إنشاء مشغّلات (Launchers) ───────────────────────────
:create_launchers
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║    🚀  4/5  إنشاء مشغّلات WIDDX — Creating Launchers  ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.

:: Create bin directory
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: Determine the python path to embed in launchers
if "%METHOD%"=="2" (
    set "EMBEDDED_PYTHON=%VENV_DIR%\Scripts\python.exe"
) else (
    set "EMBEDDED_PYTHON=python"
)

:: Create widdx.bat (CLI version)
echo   📝  إنشاء widdx.bat — Creating CLI launcher...
(
echo @echo off
echo REM WIDDX Cortex — Terminal AI Assistant
echo REM Launch with: widdx or widdx [directory]
echo.
echo if not "%%1"=="" ( cd "%%1" )
echo "%EMBEDDED_PYTHON%" "%WIDDX_DIR%\main.py" %%*
) > "%BIN_DIR%\widdx.bat"

:: Create widdx-tui.bat (TUI version)
echo   📝  إنشاء widdx-tui.bat — Creating TUI launcher...
(
echo @echo off
echo REM WIDDX Cortex — Terminal AI Assistant (TUI Mode)
echo REM Launch with: widdx-tui or widdx-tui [directory]
echo.
echo if not "%%1"=="" ( cd "%%1" )
echo "%EMBEDDED_PYTHON%" "%WIDDX_DIR%\run_textual.py" %%*
) > "%BIN_DIR%\widdx-tui.bat"

echo   ✅ تم إنشاء المشغّلات بنجاح!

:: ── 5. إضافة إلى PATH ──────────────────────────────────────
:add_to_path
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║    🔗  5/5  إضافة WIDDX إلى PATH                      ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.

:: Check if already in PATH
echo %PATH% | findstr /I /C:"%BIN_DIR%" >nul
if %ERRORLEVEL% EQU 0 (
    echo   ✅ WIDDX موجود بالفعل في PATH
) else (
    echo   🔗  جاري الإضافة إلى PATH — Adding to PATH...
    setx PATH "%BIN_DIR%;%PATH%"
    if !ERRORLEVEL! EQU 0 (
        echo   ✅ تمت الإضافة بنجاح!
    ) else (
        echo   ⚠️  فشلت الإضافة التلقائية. يمكنك إضافته يدويًا:
        echo   ⚠️  أضف هذا المسار إلى PATH: %BIN_DIR%
    )
)

:: ── إنشاء اختصار سطح المكتب (اختياري) ────────────────────
:desktop_shortcut
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║    🖥️  اختصار سطح المكتب — Desktop Shortcut           ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   هل تريد إنشاء اختصار على سطح المكتب؟
echo   Create a desktop shortcut for WIDDX?
echo.
set /p "SHORTCUT=نعم/لا (Y/N) [Y]: "
if /I "%SHORTCUT%"=="" set "SHORTCUT=y"

if /I "%SHORTCUT%"=="y" (
    echo.
    echo   📌  إنشاء اختصار سطح المكتب...
    
    :: Create shortcut using PowerShell
    powershell -Command ^
        $WS = New-Object -ComObject WScript.Shell; ^
        $SC = $WS.CreateShortcut('%USERPROFILE%\Desktop\WIDDX Cortex.lnk'); ^
        $SC.TargetPath = '%BIN_DIR%\widdx-tui.bat'; ^
        $SC.WorkingDirectory = '%USERPROFILE%'; ^
        $SC.Description = 'WIDDX Cortex — Terminal AI Assistant'; ^
        $SC.Save()
    
    if !ERRORLEVEL! EQU 0 (
        echo   ✅ تم إنشاء الاختصار على سطح المكتب!
    ) else (
        echo   ⚠️  فشل إنشاء الاختصار (يمكنك إنشاؤه يدويًا)
    )
)

:: ── إكمال التثبيت ──────────────────────────────────────────
cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║                                                        ║
echo   ║    🎉  ◈  W I D D X  C O R T E X  ◈  🎉              ║
echo   ║                                                        ║
echo   ║         ✅  تم التثبيت بنجاح!                         ║
echo   ║         ✅  Installation Complete!                    ║
echo   ║                                                        ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   📌  ملخص التثبيت — Installation Summary:
echo   ───────────────────────────────────────────
echo.
echo   📂  المسار — Install Dir:  %WIDDX_DIR%
if "%METHOD%"=="2" (
echo   🛡️  بيئة افتراضية — Venv:    %VENV_DIR%
)
echo   🚀  المشغّلات — Launchers:  %BIN_DIR%
echo.
echo   🎯  كيفية الاستخدام — How to Use:
echo   ───────────────────────────────────────────
echo.
echo   ▶️  widdx              تشغيل الواجهة النصية (CLI)
echo   ▶️  widdx-tui          تشغيل الواجهة المحسنة (TUI) ★
echo   ▶️  widdx C:\project   تشغيل في مجلد معين
echo.
echo   ❓  للمساعدة — Help:    /help (داخل WIDDX)
echo.
if /I "%SHORTCUT%"=="y" (
echo   🖥️  اختصار سطح المكتب موجود — Desktop shortcut created!
)
echo.
echo   ⚠️  هام: إذا كانت هذه أول مرة، قد تحتاج إلى:
echo   ⚠️  Important: You may need to:
echo.
echo   1. إعادة تشغيل الطرفية أو فتح نافذة جديدة
echo      Restart terminal or open a new window
echo.
echo   2. تجربة الأمر: widdx-tui
echo.
echo.
echo   ───────────────────────────────────────────
echo   💡  تمتع ببرمجتك الذكية مع WIDDX! 😊
echo   💡  Enjoy smart coding with WIDDX!
echo.
pause
