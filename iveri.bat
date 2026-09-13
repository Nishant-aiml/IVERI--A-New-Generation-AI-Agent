@echo off
setlocal

title IVERI AI Agent [Sovereign Air-Gapped]

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if "%IVERI_HOME%"=="" set "IVERI_HOME=%LOCALAPPDATA%\iveri"
set "HERMES_HOME=%IVERI_HOME%"
set "IVERI_SOVEREIGN=1"

set "PY_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if "%PY_EXE%"=="" if exist "%~dp0venv\Scripts\python.exe" set "PY_EXE=%~dp0venv\Scripts\python.exe"
if "%PY_EXE%"=="" if exist "C:\Python314\python.exe" set "PY_EXE=C:\Python314\python.exe"
if "%PY_EXE%"=="" if exist "C:\Python313\python.exe" set "PY_EXE=C:\Python313\python.exe"
if "%PY_EXE%"=="" if exist "C:\Python312\python.exe" set "PY_EXE=C:\Python312\python.exe"
if "%PY_EXE%"=="" set "PY_EXE=python.exe"

set "CMD_ARG=%~1"

if "%CMD_ARG%"=="" goto :run_chat
if /i "%CMD_ARG%"=="chat" goto :run_chat
if /i "%CMD_ARG%"=="web" goto :run_web
if /i "%CMD_ARG%"=="dashboard" goto :run_web
if /i "%CMD_ARG%"=="doctor" goto :run_doctor
if /i "%CMD_ARG%"=="demo" goto :run_demo
if /i "%CMD_ARG%"=="help" goto :show_help
if /i "%CMD_ARG%"=="--help" goto :show_help
if /i "%CMD_ARG%"=="-h" goto :show_help

"%PY_EXE%" "%~dp0hermes_cli\main.py" --sovereign %*
goto :eof

:run_chat
if /i "%CMD_ARG%"=="chat" shift
echo [IVERI] Starting Sovereign Interactive REPL...
"%PY_EXE%" "%~dp0hermes_cli\main.py" --sovereign chat %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :eof

:run_web
if /i "%CMD_ARG%"=="web" shift
if /i "%CMD_ARG%"=="dashboard" shift
echo [IVERI] Starting Sovereign Web Dashboard on http://127.0.0.1:9119 ...
"%PY_EXE%" "%~dp0hermes_cli\main.py" --sovereign dashboard --host 127.0.0.1 --port 9119 %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :eof

:run_doctor
echo [IVERI] Running Sovereign System Diagnostics...
"%PY_EXE%" "%~dp0scripts\iveri_doctor.py"
goto :eof

:run_demo
echo [IVERI] Running Golden Demo on Repository Knowledge Books...
"%PY_EXE%" "%~dp0scripts\test_golden_demo_books.py"
goto :eof

:show_help
echo.
echo ===================================================================
echo     IVERI AI AGENT - Sovereign Windows Command-Line Interface
echo ===================================================================
echo.
echo Usage:
echo   iveri                 Start interactive sovereign REPL (default)
echo   iveri chat            Start interactive sovereign REPL
echo   iveri web             Start sovereign web dashboard (port 9119)
echo   iveri doctor          Run sovereign hardware and airgap diagnostics
echo   iveri demo            Execute Golden Demo on repository PDF books
echo   iveri [command]       Run any native CLI command with air-gap mode
echo.
goto :eof
