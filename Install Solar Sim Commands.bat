@echo off
setlocal DisableDelayedExpansion
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto install_py
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto install_python
echo Solar Sim requires Python 3.10 or newer.
echo Install Python 3.10-3.14 from https://www.python.org/downloads/ with Python on PATH.
if "%~1"=="" pause
exit /b 1

:install_py
py -3 -B "%~dp0install_commands.py" %*
set "solar_exit=%ERRORLEVEL%"
goto finish

:install_python
python -B "%~dp0install_commands.py" %*
set "solar_exit=%ERRORLEVEL%"

:finish
if "%~1"=="" pause
exit /b %solar_exit%
