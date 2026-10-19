@echo off
setlocal
set "PYTHONDONTWRITEBYTECODE=1"
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto run_py
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto run_python
echo Solar Sim requires Python 3.10 or newer.
echo Install it from https://www.python.org/downloads/ with Python on PATH.
pause
exit /b 1

:run_py
py -3 -B "%~dp0solar_sim.py" --plain %*
set "solar_exit=%ERRORLEVEL%"
goto finish

:run_python
python -B "%~dp0solar_sim.py" --plain %*
set "solar_exit=%ERRORLEVEL%"

:finish
if not "%solar_exit%"=="0" pause
exit /b %solar_exit%
