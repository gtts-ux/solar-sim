@echo off
setlocal DisableDelayedExpansion
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not defined TERM set "TERM=xterm-256color"
chcp 65001 >nul
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto run_py
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto run_python
echo Solar Sim requires Python 3.10 or newer.
echo Install it from https://www.python.org/downloads/ with Python on PATH.
if "%~1"=="" pause
exit /b 1

:run_py
py -3 -B "%~dp0install_commands.py" --launch-windows %*
set "solar_exit=%ERRORLEVEL%"
goto finish

:run_python
python -B "%~dp0install_commands.py" --launch-windows %*
set "solar_exit=%ERRORLEVEL%"

:finish
if "%~1"=="" if not "%solar_exit%"=="0" pause
exit /b %solar_exit%
