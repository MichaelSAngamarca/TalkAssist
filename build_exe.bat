@echo off
REM Build script for creating TalkAssist standalone executable
REM This excludes the frontend directory

echo ========================================
echo Building TalkAssist Standalone Executable
echo ========================================
echo.

REM Check if virtual environment is activated
if not defined VIRTUAL_ENV (
    echo Warning: Virtual environment not detected.
    echo It's recommended to build from within your virtual environment.
    echo.
    pause
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
echo.

REM Build the executable
echo Building executable...
pyinstaller talkassist.spec --clean --noconfirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build successful!
    echo ========================================
    echo.
    echo The executable is located in: dist\TalkAssist.exe
    echo.
    echo Note: The frontend directory has been excluded from the build.
    echo To use the web interface, run Flask separately with: --start-flask
    echo.
) else (
    echo.
    echo ========================================
    echo Build failed!
    echo ========================================
    echo.
    echo Please check the error messages above.
    echo.
)

pause

