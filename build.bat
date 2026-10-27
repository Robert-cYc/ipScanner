@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo       Building ipScanner.exe Standalone Bundle
echo ========================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

python -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing PyInstaller...
    pip install pyinstaller
)

echo [*] Packaging standalone executable with PyInstaller...
python -m PyInstaller --clean --noconfirm --onefile --name "ipScanner" --icon "icon.ico" --add-data "index.html;." server.py

if exist "dist\ipScanner.exe" (
    echo [*] Copying dist\ipScanner.exe to .\ipScanner.exe...
    copy /Y "dist\ipScanner.exe" ".\ipScanner.exe" >nul
    echo.
    echo ========================================================
    echo  [SUCCESS] ipScanner.exe is ready in project root!
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed! Check PyInstaller output above.
)
echo.
pause
