@echo off
REM ============================================================================
REM  WIDDX Cortex — Easy Uninstaller (Double-click to remove!)
REM  إلغاء تثبيت WIDDX — فقط اضغط مرتين
REM ============================================================================
chcp 65001 >nul
setlocal enabledelayedexpansion

set "BIN_DIR=%USERPROFILE%\.widdx"

cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║      ◈  W I D D X   C O R T E X  —  إلغاء التثبيت    ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   هل أنت متأكد من إلغاء تثبيت WIDDX؟
echo   Are you sure you want to uninstall WIDDX?
echo.
set /p "CONFIRM=نعم/لا (Y/N) [N]: "
if /I "%CONFIRM%"=="" set "CONFIRM=n"
if /I not "%CONFIRM%"=="y" (
    echo.
    echo   ❌ تم الإلغاء — Cancelled.
    pause
    exit /b 0
)

:: Remove desktop shortcut
echo.
echo   🗑️  جاري حذف اختصار سطح المكتب...
if exist "%USERPROFILE%\Desktop\WIDDX Cortex.lnk" (
    del "%USERPROFILE%\Desktop\WIDDX Cortex.lnk"
    echo   ✅ تم حذف الاختصار!
)

:: Remove from PATH
echo.
echo   🔗  جاري إزالة WIDDX من PATH...
set "CURRENT_PATH="
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v PATH 2^>nul') do set "CURRENT_PATH=%%b"
if not "%CURRENT_PATH%"=="" (
    set "NEW_PATH=!CURRENT_PATH:;%BIN_DIR%=!"
    if "!NEW_PATH!"=="!CURRENT_PATH!" (
        set "NEW_PATH=!CURRENT_PATH:%BIN_DIR%;=!"
    )
    if not "!NEW_PATH!"=="!CURRENT_PATH!" (
        reg add HKCU\Environment /v PATH /t REG_EXPAND_SZ /d "!NEW_PATH!" /f >nul
        echo   ✅ تمت الإزالة من PATH!
    ) else (
        echo   ℹ️  WIDDX غير موجود في PATH
    )
)

:: Remove bin directory
echo.
echo   🗑️  جاري حذف ملفات WIDDX...
if exist "%BIN_DIR%" (
    rmdir /s /q "%BIN_DIR%"
    echo   ✅ تم حذف الملفات!
)

:: Remove .widdx directory in user folder
if exist "%USERPROFILE%\.widdx" (
    rmdir /s /q "%USERPROFILE%\.widdx"
    echo   ✅ تم حذف مجلد الإعدادات!
)

cls
echo.
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║                                                        ║
echo   ║    👋  تم إلغاء تثبيت WIDDX بنجاح                     ║
echo   ║    👋  WIDDX has been uninstalled                     ║
echo   ║                                                        ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.
echo   📌  تم حذف:
echo   ✅  اختصار سطح المكتب
echo   ✅  ملفات WIDDX من %BIN_DIR%
echo   ✅  مسار WIDDX من PATH
echo.
echo   💡  إذا أردت إعادة التثبيت، شغّل install.bat مرة أخرى
echo   💡  To reinstall, run install.bat again
echo.
echo   ⚠️  يرجى إعادة تشغيل الطرفية لتفعيل التغييرات
echo   ⚠️  Please restart your terminal
echo.
pause
