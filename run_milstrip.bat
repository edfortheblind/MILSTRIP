@echo off
setlocal

rem MILSTRIP intake toolkit — current Phase 1 launcher.
rem It does not create the future Rainbow CSV and never touches a database or
rem the network. Phase 2 behavior awaits the official interface contract.
rem
rem Usage:
rem   Drag a .txt file with the raw email/ticket text onto this .bat, OR
rem   run it from a terminal:  run_milstrip.bat request.txt
rem   run it with no file to paste text directly (press Ctrl+Z then Enter when done).

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.10+ from https://www.python.org/downloads/
    echo then try again.
    pause
    exit /b 9
)

if "%~1"=="" (
    echo No file given — paste the raw request below, then press Ctrl+Z and Enter to finish.
    echo.
    python -m milstrip.cli
) else (
    python -m milstrip.cli %*
)
set "milstrip_exit=%ERRORLEVEL%"

echo.
echo Phase 1 only: no Rainbow CSV was created or uploaded.
echo See docs\USER_SOP.md for current and planned procedures.
echo.
pause
exit /b %milstrip_exit%
